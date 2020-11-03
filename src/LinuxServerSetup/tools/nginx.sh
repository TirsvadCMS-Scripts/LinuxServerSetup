#!/bin/bash
set -euo pipefail

declare -r DIR_TOOLS="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
declare -r DIR="$( cd "$DIR_TOOLS/../" && pwd )"
declare -r DIR_CONF="$( cd "$DIR/conf" && pwd )"
declare -r FILE_LOG="$( cd "$DIR/log" && pwd )/nginx.log"

declare -r ERR_CODE=1 # Miscellaneous errors
declare -r ERR_CODE_UNKNOWN_OPTION=3
declare -r ERR_CODE_UNKNOWN_DOMAIN_NAME=9 # Could not lookup any ip adresse for domain name

# Put all output to logfile
exec 3>&1 1>>${FILE_LOG} 2>&1

SITES_AVAILABLE_PATH="/etc/nginx/sites-available/"
SITES_ENABLE_PATH="/etc/nginx/sites-enabled/"

. $DIR_TOOLS/precheck.sh
. $DIR_TOOLS/functions.sh

#case $OS in
#    "Debian GNU/Linux" | "Ubuntu" )
#        [ $(dpkg-query -W -f='${Status}' net-tools 2>/dev/null | grep -c "ok installed") -eq 0 ] && { apt-get install net-tools; }
#        ;;
#    "CentOS Linux")
#        [ $(yum list --installed | grep net-tools) ]
#        ;;
#esac

nginx_compile(){
    # ffmpeg package needed by HLS
    case $OS in
        "CentOS Linux")
            install_package https://download.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
            dnf config-manager --enable PowerTools && dnf install --nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm
            install_package http://rpmfind.net/linux/epel/7/x86_64/Packages/s/SDL2-2.0.10-1.el7.x86_64.rpm
            install_package ffmpeg ffmpeg-devel
            ;;
        "Fedora")
            install_package https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
            install_package https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
            install_package ffmpeg ffmpeg-devel
            ;;
        *)
            install_package ffmpeg
            ;;
    esac

    case $OS in
        "Fedora")
            # Nginx is a program written in C, so you will first need to install a compiler tools
            dnf groupinstall -y -q 'Development Tools'
            # Install optional Nginx dependencies
            install_package perl perl-devel perl-ExtUtils-Embed libxslt libxslt-devel libxml2 libxml2-devel gd gd-devel GeoIP GeoIP-devel openssl-devel
            ;;
        "CentOS Linux")
            dnf groupinstall -y 'Development Tools'
            # OpenSSL version 1.1.1g
            curl -L https://www.openssl.org/source/openssl-1.1.1g.tar.gz && tar xzvf openssl-1.1.1g.tar.gz

            install_package perl perl-devel pcre-devel
            ;;
        *)
            # Nginx is a program written in C, so you will first need to install a compiler tools
            install_package build-essential
            # Install optional Nginx dependencies
            install_package libpcre3 libpcre3-dev libssl-dev zlib1g-dev git
            ;;
    esac
    infoscreen "Building" "NGINX $NGINX_VER"
    [ ! -d /etc/nginx ] && mkdir /etc/nginx
    cd ~
    git clone https://github.com/sergey-dryabzhinsky/nginx-rtmp-module.git --quiet
    curl -s http://nginx.org/download/nginx-$NGINX_VER.tar.gz | tar xfz -
    cd nginx-$NGINX_VER
    ./configure \
        --user=www-data \
        --with-http_ssl_module \
        --add-module=../nginx-rtmp-module \
        --with-http_v2_module \
        --conf-path=/etc/nginx/nginx.conf \
        --pid-path=/run/nginx.pid \
        --error-log-path=/var/log/nginx/error.log \
        --with-threads \
        --http-log-path=/var/log/nginx/access.log

    make -s
    make install

    # resolve a error - systemd[1]: nginx.service: Failed to parse PID from file /run/nginx.pid: Invalid argument
    [ ! -d "/etc/systemd/system/nginx.service.d" ] && mkdir /etc/systemd/system/nginx.service.d
    printf "[Service]\nExecStartPost=/bin/sleep 0.1\n" > /etc/systemd/system/nginx.service.d/override.conf

    [ ! -d "/srv/www/default/html" ] && mkdir -p /srv/www/default/html
    chown -R www-data:www-data /srv/www
    chown -R www-data:www-data /etc/nginx
    [ ! -d "/etc/nginx/sites-available" ] && sudo -H -u www-data bash -c 'mkdir -p /etc/nginx/sites-available'
    [ ! -d "/etc/nginx/sites-enabled" ] && sudo -H -u www-data bash -c 'mkdir /etc/nginx/sites-enabled'
    [ ! -d "/etc/nginx/conf.d" ] && sudo -H -u www-data bash -c 'mkdir /etc/nginx/conf.d'
    [ ! -d "/srv/www/default/hls" ] && sudo -H -u www-data bash -c 'mkdir -p /srv/www/default/hls'
    [ ! -d "/srv/www/default/rec" ] && sudo -H -u www-data bash -c 'mkdir /srv/www/default/rec'

    infoscreendone

    cp $DIR_CONF/nginx/nginx.service /lib/systemd/system/

    [ "${STUNNEL_INSTALL:-}" == "on" ] && {
        install_package stunnel4
        infoscreen "Configuration" "stunnel4"
        file="/etc/default/stunnel4"
        var1="ENABLE="
        var2="1"
        [ -f "$file" ] && {
            grep -q "$var1" "$file" && sed -i "s/^#*\($var1\).*/\1$var2/" $file || echo "$var1$var2 #added by Tirsvad Linux Server Setup" >> $file
        }
        [ -f $DIR_CONF/stunnel4/stunnel.conf ] && cp -f $DIR_CONF/stunnel4/stunnel.conf /etc/stunnel4
        systemctl enable stunnel4.service
        systemctl restart stunnel4.service
        infoscreendone
    }

    # Clean up
    cd ~
    rm -R nginx-rtmp-module
    rm -R nginx-$NGINX_VER
}

# add_domain(){

# }

usage(){
    echo "Usage:"
    echo "    nginxSetup --help                            # Display this help message."
    echo "    nginxSetup install                           # Install Nginx."
    echo "Hosting a website with ssl"
    echo "    nginxSetup add --domain example.com --letsencrypt-email admin@example.com"
    echo "    --base-www-path /srv/www/                    # Default /var/www/"
    echo "    --domainRootPath example.com/"
    echo "    --publicPath public_html/"
    exit 0
}

while [ $# -gt 0 ]; do
    case $1 in
        --help)
            usage
            exit 0
            ;;
        --nginx-ver)
            shift
            NGINX_VER=$1
            ;;
        --letsencrypt-email)
            shift
            SSL_EMAIL=$1
            ;;
        --domain)
            shift
            DOMAIN=$1
            ;;
        --basewww-path)
            shift
            BASE_PATH=$1
            ;;
        --domain-root-path)
            shift
            DOMAIN_ROOT_PATH=$1
            ;;
        --public-path)
            shift
            PUBLIC_PATH=$1
            ;;
        --)
            shift
            break
            ;;
        --*|-*)
            echo "$0: error - unrecognized option $1" 1>&2
            exit $ERR_CODE_UNKNOWN_OPTION
            ;;
        *)
            subcommand=$1;;
    esac
    shift;
done

case $subcommand in
    install)
        install_package nginx
        ;;
    compile)
        nginx_compile
        ;;
    # add_domain)
    #     [ ${DOMAIN:-} ] && { log_error "missing the argument for --domain"; exit 1 }
    #     log "addig" "domain $DOMAIN"
    #     [ ${SSL_EMAIL:-} ] && { log "" ;echo "error"; }
    #     add_domain
    #     ;;
esac
