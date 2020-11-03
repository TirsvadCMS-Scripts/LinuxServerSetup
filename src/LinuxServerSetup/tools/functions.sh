#!/bin/bash

############################################################
## screen output
############################################################
NC='\033[0m' # No Color
RED='\033[0;31m'
GREEN='\033[0;32m'
BROWN='\033[0;33m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
WHITE='\033[0;37m'
FILLING=" : ............................................................................."

infoscreen() {
	printf "%-.80b" "${BROWN}$1 ${BLUE}${2:-}${FILLING}" 1>&3
    log "$1" ${2:-}
}

infoscreendone() {
    [ ${INFOSCREENFAILED:-} ] && infoscreenfailed || {
        printf " ${GREEN}DONE${NC}\n" 1>&3
        log_succes
    }
    unset INFOSCREENFAILED
}

infoscreenfailed() {
    [ $# -eq 0 ] && {
        printf " ${RED}FAILED${NC}\n" 1>&3
        log_error "FAILED"
    } || {
        printf " ${RED}${1:-}${NC}\n" 1>&3
        log_error ${1}
    }
}

[ ! ${FILE_LOGGER_NAME:-} ] && FILE_LOGGER_NAME=install
FILE_LOGGER="$( cd "$DIR/log" && pwd )/$FILE_LOGGER_NAME.log"
touch $FILE_LOGGER

log(){
    [ ${2:-} ] && {
        printf "%-.80b" "${BROWN}$1 ${BLUE}${2:-}${FILLING}" >> $FILE_LOGGER
    } || {
        printf "${NC}${1}${NC}\n" >> $FILE_LOGGER
    }
}

log_headline(){
    var=$(date +"%T %d-%m-%Y")
    printf "${BLUE}**${NC}\n" >> $FILE_LOGGER
    printf "${BLUE}* ${1:-} ${var}${NC}\n" >> $FILE_LOGGER
    printf "${BLUE}**${NC}\n" >> $FILE_LOGGER
    unset var
}

log_succes(){
    printf " ${GREEN}DONE${NC}\n" >> $FILE_LOGGER
}

log_error(){
    printf " ${RED}${1}${NC}\n" >> $FILE_LOGGER
}

############################################################
## System tools
############################################################
get_default_hostname() {
	# Guess the machine's hostname. It should be a fully qualified
	# domain name suitable for DNS. None of these calls may provide
	# the right value, but it's the best guess we can make.
	set -- $(hostname --fqdn      2>/dev/null ||
                 hostname --all-fqdns 2>/dev/null ||
                 hostname             2>/dev/null)
	printf '%s\n' "$1" # return this value
}

## Uncapitalize a string
lower() {
	# $1 required a string
    # return an uncapitalize string
    if [ ! -n ${1:-} ]; then
        echo "lower() requires the a string as the first argument"
        return 1;
    fi

	echo $1 | tr '[:upper:]' '[:lower:]'
}

get_publicip_from_web_service() {
    curl -$1 --fail --silent --max-time 15 icanhazip.com 2>/dev/null || /bin/true
}

system_get_user_home() {
	# $1 required a user name
    # return user hame path
	cat /etc/passwd | grep "^$1:" | cut --delimiter=":" -f6
}

## Delete domain in /etc/hosts
hostname_delete() {
	# $1 required a domain name
    if [ ! -n ${1:-} ]; then
        echo "hostname_delete() requires the domain name as the first argument"
        return 1;
    fi
    if [ -z "$1" ]; then
        local newhost=${1//./\\.}
        sed -i "/$newhost/d" /etc/hosts
    fi
}

count_down() {
    echo -n "Rebooting in  " 1>&3
    for i in $(seq $1 -1 0); do
        echo -en '\b'"$i" 1>&3
        sleep 1
    done
}

install_package() {
    case $PACKAGE_HANDLER in
    "apt" )
        [[ $# -gt 0 ]] && {
            for var in $@
            do
                infoscreen "installing" "$var"
                DEBIAN_FRONTEND=noninteractive apt-get -qq install $var
                [[ $? -eq 0 ]] && infoscreendone || infoscreenfailed
            done
        }
        ;;
    "dnf" )
        [[ $# -gt 0 ]] && {
            for var in $@
            do
                infoscreen "installing" "$var"
                dnf -y -q install $var
                [[ $? -eq 0 ]] && infoscreendone || infoscreenfailed
            done
        }
        ;;
    * )
        exit 1;
        ;;
    esac
}

os_upgrade() {
    case $PACKAGE_HANDLER in
    "apt")
        apt-get -qq update
        apt-get -qq upgrade
        ;;
    "dnf")
        dnf -y -q upgrade --refresh
        dnf -y -q update
    esac
}

############################################################
## Net tools
############################################################
kill_prosses_port() {
    ## kill prosses that is listen to port number
    # $1 required a port number
    kill $(fuser -n tcp $1 2> /dev/null)
}

firewall_rule_uniq(){
    iptables-save | uniq | iptables-restore
}

firewall_rule_save(){
    case $OS in
    "Debian GNU/Linux"|"Ubuntu")
        iptables-save > /etc/iptables/rules.v4
        ip6tables-save > /etc/iptables/rules.v6
        ;;
    "CentOS Linux"|"Fedora")
        iptables-save > /etc/sysconfig/iptables
        ip6tables-save > /etc/sysconfig/ip6tables
        ;;
    esac
}

############################################################
## Param tools
############################################################
update_param_boolean() {
	# $1 required a file path
	# $2 required a search term
	# $3 required a boolean value
    if [ ! -n ${1:-} ]; then
        echo "update_param_boolean() requires the file path as the first argument"
        return 1;
    fi
    if [ ! -n ${2:-} ]; then
        echo "update_param_boolean() requires the search term as the second argument"
        return 1;
    fi
    if [ ! -n ${3:-} ]; then
        echo "update_param_boolean() requires the boolean value as the third argument"
        return 1;
    fi

	VALUE=`lower $3`
	case $VALUE in
		yes|no|on|off|true|false|0|1)
			grep -q $2 $1 && sed -i "s/^#*\($2\).*/\1 $3/" $1 || echo "$2 $3 #added by TirsvadCMS LinuxServerSetupScript" >> $1
			;;
		*)
			echo "I dont think this $3 is a boolean"
			return 1
			;;
	esac
}

update_param() {
	# $1 required a file path
	# $2 required a search term
	# $3 required a string to replace
    if [ ! -n ${1:-} ]; then
        echo "update_param() requires the file path as the first argument"
        return 1;
    fi
    if [ ! -n ${2:-} ]; then
        echo "comment_param() requires the search term as the second argument"
        return 1;
    fi
    if [ ! -n ${3:-} ]; then
        echo "comment_param() requires a string value as the third argument"
        return 1;
    fi
	grep -q $2 $1 && sed -i "s/^#*\($2\).*/$3 $2/g" $1 || echo "$3 $2 #added by TirsvadCMS Server Setup Script" >> $1
}


###################################################################################
# Webserver
###################################################################################
function ssl_certificate {
    # Required no process listen to port 80
    # $1 required a hostname
    # $2 required a email adress
    # $3 optional if set to a webserver it will autogeneret hhtps in config files
    [ ! -d "/var/www/letsencrypt/" ] && mkdir -p /var/www/letsencrypt/
    [ {$3:-} ] && {
        case $3 in
            "nginx")
                eval "certbot --nginx --redirect --keep-until-expiring --non-interactive --agree-tos -m $2 -d $1" 1>/dev/null
            ;;
            *)
            echo "$3 is not known value" 1>&2
            exit 1
            ;;
        esac
    }
    eval "certbot --nginx --redirect --keep-until-expiring --non-interactive --agree-tos -m $2 -d $1" 1>/dev/null
}