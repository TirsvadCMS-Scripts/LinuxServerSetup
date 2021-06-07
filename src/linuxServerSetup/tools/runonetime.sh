#!/bin/bash
IFS=$'\n\t'
NONINTERACTIVE="yes"

[ -f /usr/local/bin/runonetime.sh ] && rm /usr/local/bin/runonetime.sh
[ -f /etc/systemd/system/runonetime.service ] && rm /etc/systemd/system/runonetime.service

chmod 755 /usr/bin/dpkg

systemctl disable runonetime.service

while ! ping -c 1 www.google.com; do
    echo "Waiting for reply from google.com - network interface might be down..."
    sleep 1
done

cd /root/linuxServerSetup
source .env/bin/activate
python3 serverSetup.py