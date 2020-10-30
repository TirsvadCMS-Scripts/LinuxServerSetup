#!/bin/bash
set -euo pipefail
IFS=$'\t'
NONINTERACTIVE="yes"

# Setting some path
declare -r DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
declare -r DIR_TOOLS="$( cd "$DIR/tools" && pwd )"

[ ! -d $DIR/conf ] && mkdir "$DIR/conf"
declare -r DIR_CONF="$( cd "$DIR/conf" && pwd )"

[ ! -d "$DIR/log" ] && mkdir "$DIR/log"
declare -r FILE_LOG="$( cd "$DIR/log" && pwd )/install.log"

# Put all output to logfile
exec 3>&1 1>>${FILE_LOG} 2>&1

. $DIR_TOOLS/precheck.sh
. $DIR_TOOLS/functions.sh

usage(){
    echo "-u | --url <url>                        Url link to configuration" 1>&3
    echo "-s | --strip-components <number>        Strip tarball" 1>&3
    echo "--noupgrade                             No upgrade of OS package" 1>&3
    echo "-i For interaction. Without it will run and reboot without interaction" 1>&3
    echo "Examples" 1>&3
    echo "./setup.sh --url https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetupDefaultConfig/tarball/master --strip-components 2" 1>&3
}

while [ $# -gt 0 ]; do
    case $1 in
        --help )
            usage
            exit 0;
            ;;
        -i | --interactive )
            NONINTERACTIVE="no"
            ;;
        --curl-user )
            CURL_USER=$1
            shift
            ;;
        --curl-password )
            CURL_PASSWORD=$1
            shift
            ;;
        -u | --url )
            shift
            URL_SETTINGS=$1
            ;;
        -s | --strip-components )
            shift
            STRIP_COMPONENTS=$1
            ;;
        --noupgrade )
            NOUPGRADE=1
            ;;
    esac
    shift
done

install_package ntpdate
ntpdate -s time.nist.gov

cd /root/LinuxServerSetup/
regex='(https?|ftp|file)://[-A-Za-z0-9\+&@#/%?=~_|!:,.;]*[-A-Za-z0-9\+&@#/%=~_|]'
[[ ${URL_SETTINGS:-} =~ $regex ]] && {
    [ ! ${STRIP_COMPONENTS:-} ] && STRIP_COMPONENTS=0
    log 'Downloading the settings file fram $URL_SETTINGS'
    [ $CURL_USER && $CURL_PASSWORD ] && curl -L --user $CURL_USER:$CURL_PASSWORD $URL_SETTINGS  | tar xz -C /root/LinuxServerSetup --strip-components $STRIP_COMPONENTS ||
    curl -L $URL_SETTINGS | tar xz -C /root/LinuxServerSetup --strip-components $STRIP_COMPONENTS
} || {
    [ ! -f $DIR_CONF/settings.sh ] && {
        log 'Downloading the default settings file from https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetupDefaultConfig/tarball/master'
        curl -L https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetupDefaultConfig/tarball/master | tar xz -C /root/LinuxServerSetup --strip-components 2 || log_error 'Failed'
    } || log_error 'Settings file already exist'
}

. $DIR_CONF/settings.sh

[[ $NONINTERACTIVE == "yes" && ! -f /usr/local/bin/runonetime.sh ]] && {
    infoscreen "Making" "Script for first time startup to finalize install"

    cp $DIR_TOOLS/runonetime.sh /usr/local/bin/runonetime.sh
    chmod +x /usr/local/bin/runonetime.sh

echo "[Unit]
Description=Simple one time run
Requires=network-online.target
After=multi-user.target network-online.target systemd-networkd.service

[Service]
Type=simple
ExecStart=/usr/local/bin/runonetime.sh

[Install]
WantedBy=default.target
" > /etc/systemd/system/runonetime.service
    systemctl daemon-reload
    systemctl enable runonetime.service
    infoscreendone
}

[ -z ${NOUPGRADE:-} ] && {
    infoscreen "Updating" "System and software"
    case $OS in
        "Debian GNU/Linux")
            os_upgrade
            ;;
        "Ubuntu")
            os_upgrade
            ;;
        "CentOS Linux")
            install_package socat git epel-release
            os_upgrade
            ;;
        "Fedora")
            os_upgrade
            ;;
    esac
    infoscreendone
}

[ ! $NONINTERACTIVE == "yes" ] && {
    echo "Optianel do some changes in $DIR_CONF/setting.sh" 1>&3
    echo "After reboot of system" 1>&3
    echo "Login as root and execute" 1>&3
    echo "./LinuxServerSetup/main.sh" 1>&3
    exit 0
}

echo "rebooting...." 1>&3

reboot
