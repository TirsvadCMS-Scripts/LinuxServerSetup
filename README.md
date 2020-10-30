# Tirsvad CMS - Linux Server Setup
Quick webserver setup.

## Getting Started
Need a server with debian linux compatibel distibution and root access.

I am using a Linode VP server account. Get one here from 5$ a month https://www.linode.com/?r=a60fb437acdf27a556ec0474b32283e9661f2561

### First step prepare
Default server setup:

    locale-gen && apt -y install curl # Debian

    curl -L https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetup/tarball/master | tar xz -C /root/ --strip-components 2
    ./LinuxServerSetup/scripts/setup.sh

Manuel server setup:

    curl -L https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetup/tarball/master | tar xz -C /root/ --strip-components 2
    cd LinuxServerSetup

change settings.sh file as needed. If not, you will get a default server.

    nano conf/settings.sh
    ./scripts/setup.sh

Example of adding settings file to script

    curl -L https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetup/tarball/master | tar xz -C /root/ --strip-components 2
    cd LinuxServerSetup
    URL=https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetupDefaultConfig/tarball/master
    ./setup.sh --url $URL --strip-components 2

## Features
* Hardness server
    * ssh
        * option remove password login and root login
    * firewall enabled
    * Fail2ban
    * optional
        * create a user with sudo priviliged
* Nginx
    * compiled edition with RTMP for live stream / broadcasting
    * stunnel for RTPMS workaround. Facebook stream using secure connection via port 443.

## TODO
* LetsEncrypt
    * adding ssl certificate
    * Adding ssl to mutiple virhost on nginx.