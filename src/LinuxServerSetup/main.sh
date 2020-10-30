#!/bin/bash
set -euo pipefail
IFS=$'\t'
NONINTERACTIVE="yes"
export DEBIAN_FRONTEND="noninteractive"

# Setting some path
declare -r DIR="$( cd "$( dirname "$0" )" && pwd )"
declare -r DIR_TOOLS="$( cd "$DIR/tools" && pwd )"
declare -r DIR_CONF="$( cd "$DIR/conf" && pwd )"
declare -r FILE_LOG="$( cd "$DIR/log" && pwd )/install.log"

# Put all output to logfile
exec 3>&1 1>>${FILE_LOG} 2>&1

[ ! -f "$DIR_CONF/settings.sh" ] && cp "$DIR_CONF/settings.sh.default" "$DIR_CONF/settings.sh"

. $DIR_CONF/applicationVersions.sh
. $DIR_CONF/settings.sh
. $DIR_TOOLS/precheck.sh
. $DIR_TOOLS/functions.sh

while true
do {
    ping -c1 www.google.com > /dev/null && break
    log "trying to resolve dns"
    sleep 5
}
done

log "$( date +%T ) script was started"

[ ! $( which sudo ) ] && install_package sudo

# Setting default values
[ -z "${SSHD_PASSWORDAUTH:-}" ] && SSHD_PASSWORDAUTH="no"
[ -z "${SSHD_PERMITROOTLOGIN:-}" ] && SSHD_PERMITROOTLOGIN="no"

# If the machine is behind a NAT, inside a VM, etc., it may not know
# its IP address on the public network / the Internet. Ask the Internet
# and possibly confirm with user.
infoscreen "Setting" "public ip ${PUBLIC_IPV4:-}"
[ -z "${PUBLIC_IPV4:-}" ] && {
    INFOSCREENFAILED=1
    # Ask the Internet.
    GUESSED_IP="$(get_publicip_from_web_service 4)"

    [ ! -z "${GUESSED_IP:-}" ] && {
        PUBLIC_IPV4=$GUESSED_IP
        unset INFOSCREENFAILED
        printf ".${PUBLIC_IPV4: -14}"
    }
}
infoscreendone

infoscreen "Setting" "public ipv6"
[ -z "${PUBLIC_IPV4V6:-}" ] && {
    # Ask the Internet.
    GUESSED_IPV6="$(get_publicip_from_web_service 6)"

    [ ! -z "${GUESSED_IPV6:-}" ] && {
        PUBLIC_IPV4V6=$GUESSED_IPV6
        infoscreendone
    } || infoscreenfailed
}

#[ ! "${NONINTERACTIVE:-}" == "yes" ] && . $DIR/questions.sh || {
#     [ ! "${SSHD_PERMITROOTLOGIN:-}" == "yes" ] && {
#         [ ! -z "${USER_ID:-}" ] && [ ! -z "${USER_PASSWORD:-}" ] || { echo "User credential not set in config file"; exit 1; }
#         [ ! "${SSHD_PASSWORDAUTH:-}" == "yes" ] && {
#             [ ! "$SSHD_PASSWORDAUTH" == "yes" ] && [ -z "${USER_SSHKEY:-}" ] && { echo -e "Global varible USER_SSHKEY not set in config file.\nBut required as no password is acceptet for login"; exit 1; }
#         }
#     }
# }

[ ! "${SSHD_PERMITROOTLOGIN:-}" == "yes" ] && {
    [ ! -z "${USER_ID:-}" ] && [ ! -z "${USER_PASSWORD:-}" ] || { echo "User credential not set in config file"; exit 1; }
    [ ! "${SSHD_PASSWORDAUTH:-}" == "yes" ] && {
        [ ! "$SSHD_PASSWORDAUTH" == "yes" ] && [ -z "${USER_SSHKEY:-}" ] && [ ! -f $DIR_CONF/.ssh/keys ] && { echo -e "Global varible USER_SSHKEY not set in config file and there is no sshkey file.\nBut required as no password is acceptet for login"; exit 1; }
    }
}

[ ! -z "${TIMEZONE:-}" ] && {
    infoscreen "Setting" "timezone = ${TIMEZONE:-}"
    [ `timedatectl list-timezones | grep $TIMEZONE` ] && {
        timedatectl set-timezone $TIMEZONE
        infoscreendone
    } || infoscreenfailed
}

###################################################################################
# Servername
###################################################################################
[ ! -z "${SERVER_HOSTNAME:-}" ] && {
    infoscreen "Setting" "hostname ${SERVER_HOSTNAME}"
    # First set the hostname in the configuration file, then activate the setting
    hostnamectl set-hostname $SERVER_HOSTNAME
    cp /etc/hosts /etc/hosts.backup
    update_param "/etc/hosts" "${SERVER_HOSTNAME}" "127.0.0.1"
    infoscreendone
}

###################################################################################
# Creating a priviliged user
###################################################################################
[ ! -z ${USER_ID:-} ] && {
    infoscreen "Adding" "priviliged user ${USER_ID}"
    [ ! $( id -u "${USER_ID}" ) ] && useradd -create-home -s "$USER_SHELL" $( lower "$USER_ID" -p "$USER_PASSWORD" )
    case $OS in
    "Debian GNU/Linux")
        adduser "$USER_ID" sudo
        ;;
    "Ubuntu")
        adduser "$USER_ID" sudo
        ;;
    "CentOS Linux")
        usermod -aG wheel "$USER_ID"
        ;;
    esac
    USER_HOME=`system_get_user_home "$USER_ID"`
    [ ! -d "$USER_HOME/.ssh" ] && sudo -u "$USER_ID" mkdir "$USER_HOME/.ssh"
    [ -f $DIR_CONF/.ssh/keys ] && {
        cp -f $DIR_CONF/.ssh/keys $USER_HOME/.ssh/authorized_keys
        chown $USER_ID:$USER_ID $USER_HOME/.ssh/authorized_keys
        chmod 0600 "$USER_HOME/.ssh/authorized_keys"
    }
    [ ! -z ${USER_SSHKEY:-} ] && {
        [ ! -f "$USER_HOME/.ssh/authorized_keys" ] && sudo -u "$USER_ID" touch "$USER_HOME/.ssh/authorized_keys"
        sudo -u "$USER_ID" echo "$USER_SSHKEY" >> "$USER_HOME/.ssh/authorized_keys"
        chmod 0600 "$USER_HOME/.ssh/authorized_keys"
    }
    infoscreendone

    [ ! "$SSHD_PASSWORDAUTH" == "yes" ] && [ ! -f "$USER_HOME/.ssh/authorized_keys" ] && {
        dialog --title "copy client " \
            --colors \
            --msgbox \
            "Done on client side now before we securing server\n
            \Z4ssh-copy-id $USER_ID@$PUBLIC_IPV4\n
            \n\Z0NOTE: Be sure the client side have openssh\n
            \Z4sudo $PACKAGE_HANDLER install openssh-client" 0 0 1>&3
    }
}

###################################################################################
# Hardness server
###################################################################################
infoscreen "securing" "sshd"
update_param_boolean "/etc/ssh/sshd_config" "PermitRootLogin" "$SSHD_PERMITROOTLOGIN"
update_param_boolean "/etc/ssh/sshd_config" "PasswordAuthentication" "$SSHD_PASSWORDAUTH"
systemctl reload sshd
infoscreendone

install_package fail2ban
cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sed -i "s/logpath = %(sshd_log)s/logpath = %(sshd_log)s\nenabled = true/" /etc/fail2ban/jail.local
systemctl enable fail2ban

case $OS in
    "Fedora"|"CentOS Linux")
        install_package iptables-services
        systemctl mask firewalld.service
        systemctl enable iptables.service
        systemctl enable ip6tables.service
        systemctl stop firewalld.service
        ;;
esac

infoscreen "config" "firewall"

[ -f $DIR_CONF/iptables/v4 ] && iptables-restore $DIR_CONF/iptables/v4
[ -f $DIR_CONF/iptables/v6 ] && ip6tables-restore $DIR_CONF/iptables/v6

infoscreendone

###################################################################################
# Nginx
###################################################################################
[[ ! ("${NGINX_INSTALL:-}" == "on" && "${NGINX_COMPILE:-}" == "on" ) ]] && {

    [ ! $(id -u www-data) ] && useradd www-data --user-group -s /sbin/nologin

    [ "${NGINX_INSTALL:-}" == "on" ] && {
        infoscreen "installing" "nginx"
        $DIR_TOOLS/nginx.sh install
        infoscreendone
    }

    [ "${NGINX_COMPILE:-}" == "on" ] && {
        infoscreen "building" "nginx $NGINX_VER"
        $DIR_TOOLS/nginx.sh compile --nginx-ver $NGINX_VER
        infoscreendone
        install_package stunnel4
        [ -f $DIR_CONF/stunnel4/stunnel.conf ] && cp -f $DIR_CONF/stunnel4/stunnel.conf /etc/stunnel/
    }

    [ -f $DIR_CONF/nginx/nginx.conf ] && cp $DIR_CONF/nginx/nginx.conf /etc/nginx/
    [ -d $DIR_CONF/nginx/sites-available ] && cp $DIR_CONF/nginx/sites-available/* /etc/nginx/sites-available/

    find /etc/nginx/sites-available -type f -print0 | while IFS= read -r -d $'\0' file; do ln -s $file /etc/nginx/sites-enabled/ ; done

    [ -d $DIR_CONF/websites ] && cp -rf $DIR_CONF/websites/www /srv/

    chown -R www-data:www-data /etc/nginx
    chown -R www-data:www-data /srv/www

    # Allow HTTP and HTTPS connections from anywhere
    # (the normal ports for web servers).
    iptables -A INPUT -p tcp --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
    iptables -A INPUT -p tcp --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT

    # Allow HTTP and HTTPS connections from anywhere
    # (the normal ports for web servers).
    ip6tables -A INPUT -p tcp --dport 80 -m state --state NEW,ESTABLISHED -j ACCEPT
    ip6tables -A INPUT -p tcp --dport 443 -m state --state NEW,ESTABLISHED -j ACCEPT

    [ "${NGINX_COMPILE:-}" == "on" ] && {
        [[ ( -f /srv/www/default/html/live.html  &&  ! -z "${PUBLIC_IPV4:-}" ) ]] && sed -i "s@HOSTNAME_OR_IP@$PUBLIC_IPV4@g" /srv/www/default/html/live.html
        iptables -A INPUT -p tcp --dport 1935 -m state --state NEW,ESTABLISHED -j ACCEPT # rtmp for live broadcasting
        cat $DIR_CONF/nginx/rtmp.conf >> /etc/nginx/nginx.conf
    } || {
        [ -f /srv/www/default/html/live.html ] && rm /srv/www/default/html/live.html
    }

    systemctl daemon-reload
    systemctl restart nginx
    systemctl enable nginx

} || echo "Your settings.sh file have configuration error\nNGINX_INSTALL and NGINX_COMPILE can't both be set to 'on'"

###################################################################################
# LetsEncrypt
###################################################################################
[ "${LETSENCRYPT_INSTALL:-}" == "on" ] && {
    regex="^[a-z0-9!#\$%&'*+/=?^_\`{|}~-]+(\.[a-z0-9!#$%&'*+/=?^_\`{|}~-]+)*@([a-z0-9]([a-z0-9-]*[a-z0-9])?\.)+[a-z0-9]([a-z0-9-]*[a-z0-9])?\$"
    [[ ! ${LETSENCRYPT_EMAIL}=~$regex ]] && {
        log "LETSENCRYPT_EMAIL value is not a valid email adress"
    } || {
        [ "${NGINX_INSTALL:-}" == "on" ] && install_package python-certbot-nginx
        [ ! -Z "${NGINX_SITES_HOSTNAMES:-}"] && {
            for HOSTNAME in "${NGINX_SITES_HOSTNAMES[@]}"
            do
                $DIR_TOOLS/nginx.sh add --domain $HOSTNAME --email $LETSENCRYPT_EMAIL
                log "ssl certificate for $HOSTNAME"
            done
        }
    }
}

###################################################################################
# Database
###################################################################################
[ "${POSTGRESQL_INSTALL:-}" == "yes" ] && {
    install_package progresql postgresql-contrib
}

###################################################################################
# Bash stuff
###################################################################################
[ "${BASH_STUFF:-}" == "on" ] && {
    infoscreen "Setting" "bash stuff for root - $OS version $OS_VER"
    case $OS in
    'Debian GNU/Linux'|'Ubuntu')
        # working with Debian 9
        sed -i -e "s/^# export LS_OPTIONS='--color=auto'/export LS_OPTIONS='--color=auto'/" /root/.bashrc
        sed -i -e "s/^# alias l='ls \$LS_OPTIONS -lA'/alias l='ls \$LS_OPTIONS -lA'/" /root/.bashrc
    ;;
    esac
    infoscreendone
}

[ ! "${NONINTERACTIVE:-}" == "yes" ] && {
    count_down 9
}

###################################################################################
# Extra scripts
###################################################################################
[ -f $DIR_CONF/autorun.sh ] && bash $DIR_CONF/autorun.sh

reboot