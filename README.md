# Tirsvad CMS - Linux Server Setup

Quick webserver setup.

## Getting Started

Need a server with debian linux compatibel distibution and root access.

I am using a Linode VP server account. Get one here from 5$ a month <https://www.linode.com/?r=a60fb437acdf27a556ec0474b32283e9661f2561>

### First step

#### debian

    apt-get update
    locale-gen && export LC_ALL="en_US.UTF-8" && apt-get -y install curl

Default server setup:

    curl --output serverSetup.tar.gz -L https://api.github.com/repos/TirsvadCMS-Scripts/LinuxServerSetup/tarball
    tar -xzf serverSetup.tar.gz "$(tar -tzf serverSetup.tar.gz | head -1 )src" --strip 2
    cd LinuxServerSetup
    python3 install.py --strip-components 2

Manuel server setup:

    curl --output serverSetup.tar.gz -L https://api.github.com/repos/TirsvadCMS-Scripts/LinuxServerSetup/tarball
    tar -xzf serverSetup.tar.gz "$(tar -tzf serverSetup.tar.gz | head -1 )src" --strip 2
    cd LinuxServerSetup

change settings.sh file as needed. If not, you will get a default server.

    python3 install.py --strip-components 2
    nano conf/settings.yaml
    cd /root/linuxServerSetup && . .env/bin/activate && python3 serverSetup.py

Example of adding settings file to script

    curl -L https://api.github.com/repos/TirsvadCLI-Tools/LinuxServerSetup/tarball | tar zx -C /root/ --strip-components 2
    cd LinuxServerSetup
    URL=https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetupDefaultConfig/tarball/master
    ./setup.sh --url $URL --strip-components 2

## Features

* Hardness server
  * ssh
    * option remove password login and root login
  * firewall enabled (nftables)
  * Fail2ban
  * optional
    * create a user with sudo priviliged
* Nginx
  * compiled edition with RTMP for live stream / broadcasting
  * stunnel for RTPMS workaround. Facebook stream using secure connection via port 443.
* Certbot (LetsEncrypt)
  * adding ssl certificate

## TODO

* rtmp user access via django
  * access right for yt, fb and others streaming services
