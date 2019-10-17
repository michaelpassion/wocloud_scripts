# coding: utf-8
# author: 尹帅

import os
import pymysql
import requests
import toml
import pymongo
import time

# 连接数据库
def connectMysql(database='nova'):
    ip = getManagementSever()
    db = pymysql.connect(host=ip, user='wocloud', password='wocloud@123',
                         port=3306, db=database, connect_timeout=3)
    if db != None:
        return db
    else:
        print '%s  ipv4地址格式错误，无法建立数据库连接' % ip
        exit(1)


# 查询
def query(db, sql, fetch_all):
    cursor = db.cursor()
    try:
        cursor.execute(sql)
        if fetch_all:
            return cursor.fetchall()
        else:
            return cursor.fetchone()
    except Exception as e:
        raise e
        print "sql execute error"


# 从hosts文件中读取控制节点地址
def getManagementSever():
    with open('/etc/telegraf/cmdb.conf', 'r') as f:
        return toml.load(f)['ip']

# 从mysql 数据库中读取所有运行状态的虚机信息


def getRunningHostformMysql(db):

    sql = 'select uuid from instances where power_state = 1'
    runningInstances = query(db, sql, True)
    runningSet = set()
    db.close()
    for uuid in runningInstances:
        runningSet.add(uuid[0])
    return runningSet


# 找到天融信镜像创建的虚机信息
def getTRXhosts(ip):
    # 找到天融信的镜像uuid
    db = connectMysql(ip, database='glance')

    sql = "select id from images where name like '%trx%'"
    trxuuid = query(db, sql, True)
    uuidStr = '(' + ",".join(["'%s'" % x[0] for x in trxuuid]) + ')'
    db.close()

    # 找到以天融信为镜像创建的虚机
    db = connectMysql(ip)
    sql = 'select uuid from instances where power_state = 1 and image_ref in %s' % uuidStr
    trxHost = query(db, sql, True)
    db.close()
    runningSet = set()
    for uuid in trxHost:
        runningSet.add(uuid[0])
    return runningSet


# 从 influxdb中读取最近5分钟有监控信息上报的虚机
def getInfluxdbServer():
    conf = {}
    with open('/etc/telegraf/cmdb.conf', 'r') as f:
        conf = toml.load(f)
        return conf['influx_url'][0]


def getRunningHostfromInflux(url):
    url = url + '/query?pretty=true'
    parameter = {'db': 'telegraf', 'q': 'SHOW TAG VALUES FROM vm_linux_system WITH KEY = "vm_uuid" WHERE time >= now() -5m;SHOW TAG VALUES FROM vm_win_system WITH KEY = "vm_uuid" WHERE time >= now() -5m'}
    reResult = requests.get(url, parameter).json()

    values = []
    for statement in reResult['results']:
        if statement.has_key('series'):
            hosts = statement['series'][0]['values']
	    values += hosts
    hostsSet = set()

    for value in values:
        hostsSet.add(str(value[1]))

    return hostsSet

# write not report metrix hosts to mongo


def getUnreportedHostInfo(uuids):
    fall_to_report_hosts_info = {}
    uuidList = list(uuids)
    uuidStr = ','.join(map(lambda x: "'" + x + "'", uuidList))
    sql = "select id, image_id,network_id,instance_name from instances where id in (%s) " % uuidStr
    db = connectMysql('miner')
    result = query(db, sql, True)
    fall_to_report_hosts_info = map(lambda x: {'uuid': x[0], 'image': x[
                                    1], 'network_id': x[2], 'instance_name': x[3]}, result)
    return fall_to_report_hosts_info


def writeToMongo(data):
    host='localhost'
    client = pymongo.MongoClient(host)
    db_mongo=client['db_mongo']
    db_mongo.authenticate("wocloud", "123456")
    collection = db_mongo['unReportedHosts']

    # clear history data
    if collection.count() != 0:
        collection.remove()
        
    for values in data:
        collection.insert(values)
def getHostsFromMongo():
    host = 'localhost'
    client = pymongo.MongoClient(host)
    db_mongo = client['db_mongo']
    db_mongo.authenticate("wocloud", "123456")
    now = time.time()

    modifiedTime = int(time.time() * 1000 / 5 / 60) * 5 * 60

    result = db_mongo.cpu.distinct(
        'deviceVmId', {'beginTime': {'$gt': modifiedTime - 5 * 1000 * 60}})

    print result
    hosts = set(result)
    return hosts

if __name__ == '__main__':

    db = connectMysql()
    mysqlHosts = getRunningHostformMysql(db)
    mongoHosts = getHostsFromMongo()
    

    fall_to_report_hosts = mysqlHosts - mongoHosts 
    

    print fall_to_report_hosts
    fall_to_report_hosts_info = {}

    infos = getUnreportedHostInfo(fall_to_report_hosts)
    writeToMongo(infos)

    #for uuid in fall_to_report_hosts:
    #   print '%s' % uuid

    #print '5m 内共 %d 个虚机没有上传数据' % len(fall_to_report_hosts)

