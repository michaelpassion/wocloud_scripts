# coding: utf-8
# author: 尹帅

import os
import re
import pymysql
import requests
import toml


# 连接数据库
def connectMysql(ip='127.0.0.1', database='nova'):

    db = pymysql.connect(host=ip, user='wocloud', password='wocloud@wocloud',
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
    with open('/etc/hosts', 'r') as hosts:
        for line in hosts:
            if re.match('RGCC01', line):
                return line.split()[0]


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
        ip = re.findall(r'\d+.\d+.\d+.\d+', conf['influx_url'])
        return conf['influx_url'][0]


def getRunningHostfromInflux(url):
    url = url + '/query?pretty=true'
    parameter = {'db': 'telegraf', 'q': 'SHOW TAG VALUES FROM vm_linux_system WITH KEY = "host" WHERE time >= now() -5m;SHOW TAG VALUES FROM vm_win_system WITH KEY = "host" WHERE time >= now() -5m'}
    reResult = requests.get(url, parameter).json()

    values = reResult['results'][0]['series'][0]['values'] + \
        reResult['results'][1]['series'][0]['values']
    hostsSet = set()

    for value in values:
        hostsSet.add(str(value[1]))

    return hostsSet


if __name__ == '__main__':

    # rgcc = getManagementSever()
    rgcc = raw_input("请管理节点地址，如在管理节点上运行脚本请回车: ")
    print rgcc
    if rgcc == '':
        rgcc = '172.18.96.247'
    db = connectMysql(rgcc)
    mysqlHosts = getRunningHostformMysql(db)
    influxServer = getInfluxdbServer()
    influxhosts = getRunningHostfromInflux(influxServer)
    trxHost = getTRXhosts(rgcc)

    # print mysqlHosts
    fall_to_report_hosts = mysqlHosts - influxhosts - trxHost

    for uuid in fall_to_report_hosts:
        print '%s' % uuid

    print '5m 内共 %d 个虚机没有上传数据' % len(fall_to_report_hosts)
