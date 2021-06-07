#!/usr/bin/env python3
import sys, os
import subprocess
import errno
import logging
import argparse
import shutil

class run_bash(subprocess.Popen):
    def __init__(self, args, shell=True, stdin=None, stdout=open('/dev/null', 'wb'), stderr=open(os.devnull,"wb"), executable='/bin/bash', cwd=None, **kwargs):
        subprocess.Popen.__init__(self, args=args, shell=shell, stdin=stdin, stdout=stdout, stderr=stderr, executable=executable, cwd=cwd, **kwargs)

class main(object):
    _logger = logging.getLogger(__name__)
    _path_conf: str
    _path_tools: str
    _path_log: str
    _file_log: str
    _package_handler: object
    _args: object

    def __init__(self):
        parser = argparse.ArgumentParser(description='Quick server setup based on your choises')
        parser.add_argument('--user', help='User for access download of configuration files')
        parser.add_argument('--token', help='User token for access download of configuration files')
        parser.add_argument('-u', '--url', help='an url path to configuration files')
        parser.add_argument('-s', '--strip-components', metavar='NUMBER', type=int, help='strip NUMBER leading components from tarbal file')
        parser.add_argument("-l", "--log", dest="logLevel", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help="Set the logging level")
        parser.add_argument('--noupgrade', help='do not upgrade OS')
        parser.add_argument('-i', '--interaction', action='store_true', help='For interaction. Without it will run and reboot without interaction')

        self._args = parser.parse_args()

        self._path_conf = os.path.dirname( os.path.realpath(__file__)) + '/conf'
        self._path_tools = os.path.dirname( os.path.realpath(__file__)) + '/tools'
        self._file_log = os.path.dirname( os.path.realpath(__file__)) + '/log' + '/install.log'

    def _is_root(self):
        return os.geteuid() == 0

    def _is_sudo(self):
        return os.getenv("SUDO_USER") != None

    def _is_venv(self):
        return (sys.prefix == (os.path.dirname(os.path.realpath(__file__))+"/.env"))

    def _is_os_compatible(self):
        import yaml
        with open(self._path_conf + '/osCompatibility.yaml') as f:
            osCompatibleList = yaml.load(f, Loader=yaml.FullLoader)
            for key in osCompatibleList['os']:
                if not self._package_handler._distro[0] in key:
                    self._logger.error(self._package_handler._distro[0] + ' not supportet')
                    exit()
                else:
                    for key2 in key[self._package_handler._distro[0]]:
                        if not int(self._package_handler._distro[1]) in key2['version']:
                            self._logger.critical(self._package_handler._distro[1] + ' not may not be supportet')

    def prepare_first_boot(self):
        self._logger.info('Prepare file for autorun at reboot')
        lines = [
            '[Unit]',
            'Description=Simple one time run',
            'Requires=network-online.target',
            'After=multi-user.target network-online.target systemd-networkd.service',
            '',
            '[Service]',
            'Type=simple',
            'ExecStart=/usr/local/bin/runonetime.sh',
            '',
            '[Install]',
            'WantedBy=default.target',
            '',
        ]
        with open("/etc/systemd/system/runonetime.service", "w") as f:
            for line in lines:
                f.write(line+'\n')
            f.close()

        run_bash('cp ' + self._path_tools + '/runonetime.sh /usr/local/bin/runonetime.sh').wait()
        run_bash('chmod +x /usr/local/bin/runonetime.sh').wait()
        run_bash('systemctl enable runonetime.service').wait()

    def run(self):
        self._logger.info("Install script started")

        if not self._is_root() and not self._is_sudo():
            raise OSError(errno.EACCES, 'Permission denied running this script.')

        # if not in virtualenv then create
        if not self._is_venv():
            if shutil.which('apt-get') is not None:
                run_bash('DEBIAN_FRONTEND=noninteractive apt-get install -qq virtualenv').wait()
            elif shutil.which('dnf') is not None:
                run_bash('dnf install --assumeyes virtualenv').wait()
            elif shutil.which('yum') is not None:
                run_bash('yum install virtualenv').wait()
            else:
                self._logger.error('Failed to install')
                self._logger.error('Could not find program {apt-get, dnf, yum]')
                exit(1)
            if not os.path.exists(os.path.dirname(os.path.realpath(__file__))+"/.env"):
                self._logger.info("Creating Virtual envoriment")
                proc = run_bash('virtualenv -p python3 .env')
                if (proc.wait()):
                    self._logger.error('Failed to create virtual envoriment')
                    exit('wrong')
            self._logger.info('Virtual envoriment being set')
            activate_this = os.path.dirname( os.path.realpath(__file__)) + '/.env/bin/activate_this.py'
            with open(activate_this) as f:
                code = compile(f.read(), activate_this, 'exec')
                exec(code, dict(__file__=activate_this))
            run_bash('pip' + ' install PyYAML ', stdout=subprocess.PIPE).wait()

        # if run_bash("python3" + " -m pip --version", shell=True,  stdin=None, executable='/bin/bash').wait():
        #     run_bash("curl" + " https://bootstrap.pypa.io/get-pip.py -o get-pip.py",  shell=True,  stdin=None, executable='/bin/bash').wait()
        #     run_bash("python3" + " get-pip.py", shell=True,  stdin=None, executable='/bin/bash').wait()

        self._logger.info("Running in Virtual envoriment")
        run_bash('pip install --upgrade pip ').wait()
        run_bash('pip install -e .')
        run_bash('pip install package-manager-TirsvadCLI ').wait()

        from packageManager.manager import packageManager
        self._package_handler=packageManager()

        self._is_os_compatible()

        if self._args.url:
            arg=''
            arg2=''
            if self._args.strip_components:
                arg2 += arg2 + " --strip-components " + str(self._args.strip_components)
            if self._args.user and self._args.token:
                arg += arg + " --user " + self._args.user + ":" + self._args.token
            elif self._args.user:
                self._logger.warning('Missing token / password for user')
            elif self._args.token:
                self._logger.warning('Missing user for password / token')
            arg += ' -L ' + self._args.url
            self._logger.info('Downloading user defined configuration')
            run_bash('curl --silent' + arg + ' | tar -xz -C /root/linuxServerSetup ' + arg2).wait()
        else:
            self._logger.info('Downloading default configuration')
            run_bash('curl --silent -L https://github.com/TirsvadCMS-Bashscripts/LinuxServerSetupDefaultConfig/tarball/python | tar xz -C /root/linuxServerSetup --strip-components 2').wait()

        if not self._args.noupgrade:
            self._package_handler.system_upgrade()

        self._package_handler.install('ntpdate')
        run_bash('ntpdate -s time.nist.gov').wait()

        if not self._args.interaction:
            self.prepare_first_boot()
            os.system('reboot')
        else:
            print('Optianel do some changes in ' + self._path_conf + '/setting.sh')
            print('After reboot of system')
            print('Login as root and execute file below from virtual envoriment')
            print('cd ' + os.path.dirname( os.path.realpath(__file__) ) + ' && . .env/bin/activate')
            print('python3 serverSetup.py')

if __name__ == "__main__":
    if not os.path.exists( os.path.dirname( os.path.realpath(__file__)) + '/log'):
        os.makedirs( os.path.dirname( os.path.realpath(__file__) ) + '/log')
    chdlr = logging.StreamHandler()
    chdlr.setLevel(logging.INFO)
    chdlr.setFormatter(logging.Formatter('%(name)s - [%(levelname)s]: %(message)s'))
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)',
        handlers=[
            logging.FileHandler(os.path.dirname( os.path.realpath(__file__)) + '/log' + '/main.log', mode='w'),
            chdlr
            ]
    )
    app = main()
    app.run()