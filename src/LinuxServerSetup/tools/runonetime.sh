#!/bin/bash
IFS=$'\n\t'
NONINTERACTIVE="yes"

[ -f /usr/local/bin/runonetime.sh ] && rm /usr/local/bin/runonetime.sh
[ -f /etc/systemd/system/runonetime.service ] && rm /etc/systemd/system/runonetime.service

cd /root/LinuxServerSetup

#defaulttarget

bash main.sh

systemctl disable runonetime.service