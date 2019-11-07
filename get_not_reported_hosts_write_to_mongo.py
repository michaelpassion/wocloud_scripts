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
    db = pymysql.connect(host=ip, user=database, password=database,
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


def getRunningHostformMysql(db):
    sql = 'select uuid from instances where power_state = 1'
    runningInstances = query(db, sql, True)
    runningSet = set()
    db.close()
    for uuid in runningInstances:
        runningSet.add(uuid[0])
    return runningSet


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
    host = 'localhost'
    client = pymongo.MongoClient(host)
    db_mongo = client['db_mongo']
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

    modifiedTime = int(time.time() / 5 / 60) * 5 * 60 * 1000

    result = db_mongo.cpu.distinct(
        'deviceVmId', {'beginTime': {'$gt': modifiedTime - 10 * 1000 * 60}})

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
