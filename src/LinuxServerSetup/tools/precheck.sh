# check if running as root
[[ $EUID -ne 0 ]] && {
    echo "This script must be run as root."
    exit
}

unsupported_os_ver(){
    echo "Unsupported OS version $OS $OS_VER" | tee /dev/fd/3
    exit 1;
}

[ -z "${OS_COMBATIBLE:-}" ] || [ "${OS_COMBATIBLE:-}" ] && {
    # check running compatible system
    [ -f /etc/os-release ] && {
        # freedesktop.org and systemd
        . /etc/os-release
        OS=$NAME
        OS_VER=$VERSION_ID
    } || {
        # Fall back to uname, e.g. "Linux <version>", also works for BSD, etc.
        OS=$(uname -s)
        OS_VER=$(uname -r)
    }

    case $OS in
        "Debian GNU/Linux")
            PACKAGE_HANDLER="apt"
            OS_COMBATIBLE=true
            ;;
        "Ubuntu")
            PACKAGE_HANDLER="apt"
            OS_COMBATIBLE=true
            ;;
        "CentOS Linux")
            PACKAGE_HANDLER="dnf"
            [[ "$OS_VER" -ge "8" ]] && OS_COMBATIBLE=true || unsupported_os_ver
            ;;
        "Fedora")
            PACKAGE_HANDLER="dnf"
            [[ "$OS_VER" -ge "30" ]] && OS_COMBATIBLE=true || unsupported_os_ver
            ;;
        *)
            echo "Unsupported OS $OS" | tee /dev/fd/3
            exit 1
            ;;
    esac
}
