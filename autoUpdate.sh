#!/bin/bash
#Program:
#   update telegraf agent and config automatically, saving user from downloading agent package
#   or modify config files
#History:
#2019-08-27 yinshuai  First release


# If not specify, default meaning of return value:
# 0: Success
# 1: System error
# 2: Application error
# 3: Network error

CUR_VER=""
NEW_VER=""

CONF_SRC="telegraf.conf"
CONF_DEST="/etc/telegraf/telegraf.conf"

CMD_INSTALL=""
CMD_UPDATE=""
SOFTWARE_UPDATED=0

SYSTEMCTL_CMD=$(command -v systemctl 2>/dev/null)
SERVICE_CMD=$(command -v service 2>/dev/null)


PACKAGE_URL="http://169.254.169.254:10051/linux/"
RPM_PACKAGE="telegraf-1.5.2-190826.WoCloud.x86_64.rpm"
DEB_PACKAGE="telegraf_1.5.2-190216.WoCloud_amd64.deb"
CONF="telegraf.conf"

#######color code########
RED="31m"      # Error message
GREEN="32m"    # Success message
YELLOW="33m"   # Warning message
BLUE="36m"     # Info message


#########################

###############################
colorEcho(){
    COLOR=$1
    echo -e "\033[${COLOR}${@:2}\033[0m"
}

downloadTelegraf(){
    colorEcho ${BLUE} "Downloading telegraf agent ..."

    if [[ -f /etc/redhat-release ]] || [[ -f /etc/SuSE-release ]]; then
        # RHEL-variant logic
        DOWNLOAD_LINK=${PACKAGE_URL}${RPM_PACKAGE}
        echo ${DOWNLOAD_LINK}

        curl -L -H "Cache-Control: no-cache" -o /tmp/${RPM_PACKAGE} ${DOWNLOAD_LINK}


    elif [[ -f /etc/debian_version ]]; then
    # Debian/Ubuntu logic
        DOWNLOAD_LINK=$PACKAGE_URL$DEB_PACKAGE
        echo $DOWNLOAD_LINK
        curl -L -H "Cache-Control: no-cache" -o /tmp/${DEB_PACKAGE} ${DOWNLOAD_LINK}
    fi

    if [ $? != 0 ]; then
        colorEcho ${RED} "Failed to download! Please check your network or try again."
        return 3
    fi
    return 0
}


installSoftware(){
    if [[ -f /etc/redhat-release ]] || [[ -f /etc/SuSE-release ]]; then
        rpm -ivh /tmp/$RPM_PACKAGE
    elif [[ -f /etc/debian_version ]]; then
        dpkg -i /tmp/$DEB_PACKAGE
    fi
    if [[ $? -ne 0 ]]; then
        colorEcho ${YELLOW} "安装 telegraf agent 失败,请联系开发人员查看原因"
        return 1
    fi
}

modifyConfig(){
    colorEcho ${BLUE} "Downloading telegraf agent config file ..."

    DOWNLOAD_LINK=$PACKAGE_URL$CONF_SRC
    curl -L -H "Cache-Control: no-cache" -o ${CONF_DEST} ${DOWNLOAD_LINK}
    echo ${DOWNLOAD_LINK}
    if [[ $? -ne 0 ]]; then
        colorEcho ${YELLOW} "无法从远程获取配置文件，请手动创建文件后重试"
        return 3
    fi

    UUID=`curl --connect-timeout 10 http://169.254.169.254/openstack/2013-10-17/meta_data.json | python -c "import json,sys;obj=json.load(sys.stdin);print obj['uuid']" 2>/dev/null`

    if [[ $? -ne 0 ]]; then
        colorEcho ${YELLOW} "无法获取虚机 UUID 请确认nova meta_data 服务正常"
        return 1
    fi
        colorEcho ${RED} "UUID "${UUID}
    if [[ -f ${CONF_DEST} ]]; then
        colorEcho ${GREEN} "修改配置文件"
        sed -i "s/bd6d784a-3da7-41e0-bc7f-b1d7e4e3880c/${UUID}/g" ${CONF_DEST}
    else
        colorEcho ${YELLOW} "配置文件不存在，无法修改uuid"
            return 1
    fi

    return 0
}

main(){
    downloadTelegraf
    modifyConfig
    installSoftware
    colorEcho ${GREEN} "telegraf 安装成功"
}

main

