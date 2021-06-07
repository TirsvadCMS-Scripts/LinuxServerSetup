#!/usr/bin/env python3

import os, sys, errno
import shutil
import logging
import subprocess
import yaml
import argparse
import pwd, grp
import distro
import fileinput
from packageManager.manager import packageManager
import secrets
import string

def copyTree(src, dst, symlinks=False, endswithFilter=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copyTree(s, d, symlinks, endswithFilter)
        else:
            if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                if (endswithFilter and s.endswith(endswithFilter)) or not endswithFilter:
                    shutil.copy2(s, d)

class preCheck():
    _logger = logging.getLogger(__name__)
    _distro = distro.linux_distribution(full_distribution_name=False)

    def check_uid(self):
        if not (os.geteuid() == 0):
            if not 'SUDO_UID' in os.environ.keys():
                self._logger.error("This program requires super user priv.")
                sys.exit(1)

    def is_os_compatible(self, osCompatibleList: list):
        for key in osCompatibleList['os']:
            if not self._distro[0] in key:
                self._logger.error(self._distro[0] + ' not supportet')
                exit()
            else:
                for key2 in key[self._distro[0]]:
                    if not int(self._distro[1]) in key2['version']:
                        self._logger.critical(self._distro[1] + ' not may not be supportet')

class nginxManager():
    _logger: object = logging.getLogger(__name__)
    _packageHandler: object = packageManager()
    _nginx_user = 'www-data'
    _nginx_group = 'www-data'
    _uid: int
    _gid: int
    _apps: dict

    def __init__(self, osApps:dict):
        self._logger.info('nginxManager script started')
        self._apps = osApps

    def _if_not_dir_create(self, path, uid, gid):
        if not os.path.exists(path):
            os.makedirs(path)
        os.chown(path, uid, gid)

    def setUser(self, user: string = 'www-data'):
        self._nginx_user = user

    def setGroup(self, group: string = 'www-data'):
        self._nginx_group = group

    def systemctl(self, enable=True, autostart=True):
        if enable: runBash('systemctl enable nginx').wait()
        if autostart: runBash('systemctl start nginx').wait()

    def compile(self, cwd: str = '/root'):
        try:
            pwd.getpwnam(self._nginx_user)
        except KeyError:
            self._logger.debug('groupadd and useradd ' + self._nginx_group + ':' + self._nginx_user)
            runBash('groupadd ' + self._nginx_group).wait()
            runBash('useradd -c "' + self._nginx_user + '" -r -s /sbin/nologin -g ' + self._nginx_group).wait()
        self._uid = pwd.getpwnam(self._nginx_user).pw_uid
        self._gid = pwd.getpwnam(self._nginx_group).pw_gid
        self._logger.info('Installing dependencies for building nginx with hls support')
        if 'nginx' in self._apps: nginx = self._apps['nginx']
        if 'compile' in nginx: nginx = nginx['compile']
        for nginxVersion in nginx:
            nginx = nginx[nginxVersion]
        if 'install' in nginx:
            self._packageHandler.install(nginx['install'])
        if 'cmd' in nginx:
            for item in nginx['cmd']:
                runBash(item, cwd=cwd).wait()
        if 'compileCmd' in nginx:
            cwd += '/nginx-' + nginxVersion
            for key in nginx['compileCmd']:
                runBash(nginx['compileCmd'][key], cwd=cwd).wait()
        lines = [
            '[Unit]',
            'Description=The NGINX HTTP and reverse proxy server',
            'After=syslog.target network.target remote-fs.target nss-lookup.target',
            '',
            '[Service]',
            'Type=forking',
            'PIDFile=/run/nginx.pid',
            'ExecStartPre=/usr/local/sbin/nginx -t',
            'ExecStart=/usr/local/sbin/nginx',
            'ExecReload=/bin/kill -s HUP $MAINPID',
            'ExecStop=/bin/kill -s QUIT $MAINPID',
            'PrivateTmp=true',
            '',
            '[Install]',
            'WantedBy=multi-user.target',
            '',
        ]
        with open("/etc/systemd/system/nginx.service", "w") as f:
            for line in lines:
                f.write(line+'\n')
            f.close()
        self._if_not_dir_create('/var/www', self._uid, self._gid)
        self._if_not_dir_create('/var/www/html', self._uid, self._gid)
        self._if_not_dir_create('/srv/www/default/html', self._uid, self._gid)
        self._if_not_dir_create('/etc/nginx/sites-available', self._uid, self._gid)
        self._if_not_dir_create('/etc/nginx/sites-enabled', self._uid, self._gid)
        self._if_not_dir_create('/etc/nginx/conf.d', self._uid, self._gid)
        self._if_not_dir_create('/srv/www/default/hls', self._uid, self._gid)
        self._if_not_dir_create('/srv/www/default/recl', self._uid, self._gid)

        self.systemctl()

class runBash(subprocess.Popen):
    def __init__(self, args, shell=True, stdin=None, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull,"wb"), executable='/bin/bash', cwd=None, stdoutfile=True, **kwargs):
        if stdoutfile:
            with open(os.path.dirname(os.path.realpath(__file__)) + '/log/stdout.txt','wb') as stdout, open(os.path.dirname(os.path.realpath(__file__)) + '/log/stderr.txt','wb') as stderr:
                subprocess.Popen.__init__(self, args=args, shell=shell, stdin=stdin, stdout=stdout, stderr=stderr, executable=executable, cwd=cwd, **kwargs)
        else:
            subprocess.Popen.__init__(self, args=args, shell=shell, stdin=stdin, stdout=stdout, stderr=stderr, executable=executable, cwd=cwd, **kwargs)

class serverSetup(object):
    _logger = logging.getLogger(__name__)
    _path_conf = ''
    _cfg = {}
    _apps = {}
    _parser_args = None
    _packageHandler = packageManager()
    _path_webhost_root = '/srv/'
    _path_webhost_root_user = 'root'
    _path_webhost_root_group = 'root'
    _path_nginx_sites_available = '/etc/nginx/sites-available/'
    _path_nginx_sites_enabled = '/etc/nginx/sites-enabled/'
    _path_uwsgi_config_available = '/etc/uwsgi/apps-available/'
    _path_uwsgi_config_enabled = '/etc/uwsgi/apps-enabled/'
    _path_webhost_rtmp_hls = '/mnt/hls/'
    _clean_up_cmf = [] # TODO clean up
    _dbDefault = ''

    def __init__(self):
        self._path_conf = os.path.dirname( os.path.realpath(__file__)) + '/conf/'
        self._file_log = os.path.dirname( os.path.realpath(__file__)) + '/log' + '/main.log'
        self._cfg['installSteps'] = {}

    def _parseArgs(self, args=None):
        if args == None:
            args = sys.argv[1:]
        else:
            if not '--verbose' in args:
                args += ['--verbose', '3']
        parser = argparse.ArgumentParser(prog="Linux Server Setup", description='Quick server setup based on your choices')
        parser.add_argument('--verbose', type=int, default=3, help='show logger info')
        parser.add_argument('-i', '--interaction', action='store_true', help='For interaction. Without it will run and reboot without interaction')
        self._parser_args = parser.parse_args(args=args)

    def _appsInstaller(self, app):
        if app in self._osApps:
            package = self._osApps[app]
            if 'install' in package:
                apps = package['install']
                self._packageHandler.install(apps)
            if 'uninstall' in package: # TODO make it in packageHandler
                apps = package['uninstall']
                if isinstance(apps, str):
                    runBash('apt-get -y purge ' + apps).wait()
                elif isinstance(apps, list):
                    for p in apps:
                        runBash('apt-get -y purge ' + p).wait()
            del self._osApps[app] # only once time install

    def _fileReplaceAll(self, file: str,searchExp: str,replaceExp: str):
        for line in fileinput.input(file, inplace=1):
            line = line.replace(searchExp,replaceExp)
            sys.stdout.write(line)

    def _etcAddLineToHosts(self, hostname):
        for line in fileinput.input('/etc/hosts', inplace=True):
            if not line.strip().endswith(hostname):
                sys.stdout.write(line)

        f = open('/etc/hosts', mode='a')
        f.write("\n" + '127.0.0.1  ' + hostname)
        f.write("\n" + '::1  ' + hostname)
        f.close()

    def _cfgGetFile(self):
        if not os.path.isfile(self._path_conf + 'settings.yaml'):
            self._logger.error('configuration file is missing at ' + self._path_conf + 'settings.yaml')
            exit(1)
        with open(self._path_conf + 'settings.yaml') as f:
            self._cfg.update(yaml.load(f, Loader=yaml.FullLoader))

    def _validateCfg(self):
        errorlist = []

        # ssh port validating and set default value=22 if not exist in cfg
        if 'port' in self._cfg['ssh']:
            if not type(self._cfg['ssh']['port']) == int:
                errorlist.append('sshd port value is not a number')
        else:
            if not isinstance(self._cfg['ssh']) == dict:
                self._cfg['ssh'] = dict()
            self._cfg['ssh']['port'] = 22

        if errorlist:
            for erroritem in errorlist:
                self._logger.error(erroritem)

    def _cfgGetIpAndSave(self):
        if not "publicIp4Address" in self._cfg['localHost']:
            externalIp = os.popen('curl -4 -s -m 2 https://ident.me && break').read()
            self._logger.debug('ipv4 lookup as ' + externalIp)
            if not externalIp is "":
                self._cfg['localHost'].update({'publicIp4Address': externalIp})
        if not "publicIp6Address" in self._cfg['localHost']:
            externalIp6 = os.popen('curl -6 -s -m 2 https://ident.me && break').read()
            self._logger.debug('ipv6 lookup as ' + externalIp6)
            if not externalIp6 is "":
                self._cfg['localHost'].update({'publicIp6Address': externalIp6})
        with open(self._path_conf + 'settings.yaml', 'w') as f:
            yaml.dump(self._cfg, f)

    def _cfgCreateGroup(self):
        self._logger.info('Creating groups')
        for g in self._cfg['groups']:
            if runBash('groupadd ' + g).wait():
                self._logger.warning('Failed to do \'groupadd ' + g + '\'')

    def _cfgCreateUser(self):
        self._logger.info('Creating user')
        for key in self._cfg['user']:
            arg = ''
            if not 'name' in key or key['name'] == None:
                self._logger.critical('User name is missing')
            if 'memberOfGroups' in key:
                groupList = key['memberOfGroups']
                if not groupList == None:
                    arg += ' -G ' + ','.join(groupList[0:])
            if 'shell' in key:
                arg += ' --shell ' + key['shell']
            if 'homeDirectory' in key:
                if not key['homeDirectory'] == None:
                    arg += ' --home-dir ' + key['homeDirectory']
            else:
                arg += ' -m'
            if 'password_encrypted' in key:
                if not key['password_encrypted'] == None:
                    arg += ' --password \'' + key['password_encrypted'] + '\''
            if runBash('useradd ' + key['name'] + arg).wait():
                self._logger.critical('User ' + key['name'] + ' was not created')
            else:
                self._logger.debug('useradd ' + key['name']) # TODO remove line
            if 'sshkey' in key:
                if not key['sshkey'] == None:
                    userHomeDir = subprocess.check_output('su ' + key['name'] + ' -c \'eval echo ~$USER\'', shell=True).decode('utf-8').rstrip()
                    if not os.path.exists(userHomeDir + '/.ssh'):
                        runBash('su ' + key['name'] + ' -c \'ssh-keygen -t rsa -q -f "' + userHomeDir + '/.ssh/id_rsa" -N ""\'').wait()
                        runBash('su ' + key['name'] + ' -c \'touch "' + userHomeDir + '/.ssh/authorized_keys"\'').wait()
                    with open(userHomeDir + '/.ssh/authorized_keys', 'a') as f:
                        f.write( key['sshkey'] + '\n')

    def _cfgLocalHostSetup(self):
        self._logger.info('Local host setup')
        if 'serverName' in self._cfg['localHost']:
            if runBash('hostnamectl set-hostname ' + self._cfg['localHost']['serverName']).wait():
                self._logger.critical('Hostname ' + self._cfg['localHost']['serverName'] + ' was not set')
            self._etcAddLineToHosts(self._cfg['localHost']['serverName'])
        if 'timeZone' in self._cfg['localHost'] and not self._cfg['localHost']['timeZone'] == '':
            print('timedatectl set-timezone ' + self._cfg['localHost']['timeZone'])
            runBash('timedatectl set-timezone ' + self._cfg['localHost']['timeZone']).wait()

    def _firewallSetup(self):
        if os.path.exists(self._path_conf + 'nftables'):
            self._logger.info('Setting firewall')
            copyTree(self._path_conf + 'nftables/etc', '/etc')
            runBash('systemctl enable nftables.service')

    def _cfgHardnessServer(self):
        self._logger.info('Hardness server')
        found = []
        for line in fileinput.input('/etc/ssh/sshd_config', inplace=True):
            if line.startswith('PermitRootLogin '):
                if 'permitRootLogin' in self._cfg['ssh']:
                    line = 'PermitRootLogin ' + self._cfg['ssh']['permitRootLogin'] + '\n'
                    found.append('permitRootLogin')
            elif line.startswith('PasswordAuth '):
                if 'passwordAuth' in self._cfg['ssh']:
                    line = 'PasswordAuthentication ' + self._cfg['ssh']['passwordAuth'] + '\n'
                    found.append('passwordAuth')
            elif line.startswith('Port ') or line.startswith('#Port '):
                if not found.append('port'):
                    if 'port' in self._cfg['ssh']:
                        if type(self._cfg['ssh']['port']) == int:
                            found.append('port')
                            line = 'Port ' + str(self._cfg['ssh']['port']) + '\n'
                else:
                    line = ''
            sys.stdout.write(line)

        if not 'permitRootLogin' in found:
            with open('/etc/ssh/sshd_config', 'a') as f:
                f.write('PermitRootLogin ' + self._cfg['ssh']['permitRootLogin'] + '\n')
        if not 'passwordAuth' in found:
            with open('/etc/ssh/sshd_config', 'a') as f:
                f.write('PasswordAuthentication ' + self._cfg['ssh']['passwordAuth'] + '\n')
        if not 'port' in found:
            with open('/etc/ssh/sshd_config', 'a') as f:
                f.write('Port ' + str(self._cfg['ssh']['port']) + '\n')

        with fileinput.FileInput('/etc/nftables.conf', inplace=True) as f:
            for line in f:
                print(line.replace('__ssh_port__', str(self._cfg['ssh']['port'])), end='')

    def _cfgAppsInstall(self):
        cfg = self._cfg['apps']
        if 'postgresql' in cfg:
            cfg = cfg['postgresql']
            if 'install' in cfg and cfg['install']=='install':
                self._appsInstaller('postgresql')
                self._appsInstaller('psycopg2dep')
            self._dbDefault = 'postgresql'
            if 'superuser' in cfg and 'password_encrypted' in cfg:
                runBash("su - postgres -c \"psql -c \\\"CREATE ROLE " + cfg['superuser'] + " WITH LOGIN PASSWORD '" + cfg['password_encrypted'] + "' \\\"\"").wait()

    def _cfgRtmpServer(self):
        cfg = self._cfg['rtmp']
        if 'configFile' in cfg:
            shutil.copyfile(self._path_conf + cfg['configFile'], self._path_nginx_sites_available + 'rtmp.conf')
        else:
            f = open('conf/nginx/sites-available/rtmpDefault.skeleton', mode='r')
            conf = f.read()
            f.close()
            conf = conf.replace('__hlsPath__', self._path_webhost_rtmp_hls if not 'hlsPath' in cfg else cfg['hlsPath'])
            f = open(self._path_nginx_sites_available + 'rtmpDefault.conf', mode='w+')
            f.write(conf)
            f.close()

    def _cfgWebserver(self):
        if 'nginx' in self._cfg['webserver']:
            self._logger.info('Webserver setup')
            nginxApp = nginxManager(osApps = self._osApps)
            if self._cfg['webserver']['nginx'] == 'compile':
                nginxApp.compile() # TODO parsing argument here instead of dict() in object
                shutil.copy(self._path_conf + 'nginx/index.html', '/var/www/html/index.html')
                nginxApp.systemctl()
            elif self._cfg['webserver']['nginx'] == 'install':
                pass
            else:
                self._logger.critical('did not understand command ' + self._cfg['webserver']['nginx'])
                self._logger.error('nginx server not installed')

            if os.path.exists(self._path_conf + 'nginx/sites-available'):
                copyTree(self._path_conf + 'nginx/sites-available', self._path_nginx_sites_available, endswithFilter='.conf')
                for entry in os.scandir(self._path_nginx_sites_available):
                    try:
                        os.symlink(entry, self._path_nginx_sites_enabled + entry.name)
                    except OSError as e:
                        if e.errno == errno.EEXIST:
                            os.remove(self._path_nginx_sites_enabled + entry.name)
                            os.symlink(entry, self._path_nginx_sites_enabled + entry.name)
                        else:
                            raise e

            if os.path.exists(self._path_conf + 'nginx/nginx.conf'):
                shutil.copyfile(self._path_conf + 'nginx/nginx.conf', '/etc/nginx/nginx.conf')

        if 'stunnel' in self._cfg and self._cfg['stunnel'] in ['yes', 'on', 'true', '1']: self._packageHandler.install('stunnel')
        self._packageHandler.install('uwsgi')
        self._packageHandler.install('uwsgi-plugin-python3')

        runBash('systemctl restart nginx').wait()

    def _cfgWebhost(self):
        self._logger.info('webhost configuration')
        for webhost in self._cfg['webHosts']:
            self._appsInstaller('certbot')
            self._certbot()
            if 'name' in webhost:
                self._logger.info('webhost adding - ' + webhost['name'])
                path_webhost = self._path_webhost_root + webhost['name'] if not 'path_root' in webhost else webhost['path_root']
                if not os.path.exists(path_webhost): os.mkdir(path_webhost)
                path_webhost_uid = pwd.getpwnam(self._path_webhost_root_user if not 'user' in webhost else webhost['user']).pw_uid
                path_webhost_gid = grp.getgrnam(self._path_webhost_root_group if not 'group' in webhost else webhost['group']).gr_gid
                os.chown(path_webhost, uid=path_webhost_uid, gid=path_webhost_gid)
                for virtualhost in webhost['virtualhosts']:
                    if 'virtualhost' in virtualhost:
                        self._etcAddLineToHosts(virtualhost['virtualhost'])
                        self._logger.info('virtualhost adding - ' + virtualhost['virtualhost'])
                        virtualhost_path_uid = path_webhost_uid if not 'user' in virtualhost else pwd.getpwnam(virtualhost['user']).pw_uid
                        virtualhost_path_gid = path_webhost_gid if not 'group' in virtualhost else grp.getgrnam(virtualhost['group']).gr_gid
                        sudo_cmd = 'sudo --non-interactive -u www-data -g ' + grp.getgrgid(virtualhost_path_gid).gr_name
                        if 'virtualenv' in virtualhost or 'framework' in virtualhost:
                            path_virtualhost = path_webhost + '/webapps/' + virtualhost['virtualhost'] if not 'path_relative' in virtualhost else path_webhost + '/webapps/' + virtualhost['path_relative']
                            os.makedirs(path_virtualhost, mode=0o2775)
                            os.chown(path_webhost + '/webapps/', uid=path_webhost_uid, gid=path_webhost_gid)
                        else:
                            path_virtualhost = path_webhost + '/' + virtualhost['virtualhost'] if not 'path_relative' in virtualhost else path_webhost + '/' + virtualhost['path_relative']
                            os.makedirs(path_virtualhost, mode=0o2775)
                        os.chown(path_virtualhost, uid=virtualhost_path_uid, gid=virtualhost_path_gid)

                        if 'virtualenv' in virtualhost and virtualhost['virtualenv'] =='python3':
                            if 'framework' in virtualhost:
                                framework = virtualhost['framework']
                            runBash(sudo_cmd + ' virtualenv -p python3 .env', cwd=path_virtualhost).wait()
                        if 'framework' in virtualhost:
                            framework = virtualhost['framework']
                            if 'name' in framework and framework['name'] == 'django':
                                appsname = 'website' if not 'app_name' in framework else framework['app_name']
                                if 'skeleton' in framework and framework['skeleton'] == 'yes':
                                    self._logger.info('framework skeleton install')
                                    runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && pip install wheel\'', cwd=path_virtualhost).wait()
                                    runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && pip install django\'', cwd=path_virtualhost).wait()
                                    f = open('conf/django/settings.default', mode='r')
                                    settings = f.read()
                                    f.close()
                                    if self._dbDefault == 'postgresql':
                                        runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && pip install psycopg2\'', cwd=path_virtualhost).wait()
                                        virtualhostname = virtualhost['virtualhost']
                                        virtualhostname = virtualhostname.replace('.', '')
                                        alphabet = string.ascii_letters + string.digits
                                        password = ''.join(secrets.choice(alphabet) for i in range(16))
                                        name = str(virtualhostname + appsname).replace('-','_')
                                        settings = settings.replace('__dbname__', name)
                                        settings = settings.replace('__dbuser__', name)
                                        settings = settings.replace('__dbpassword__', password)
                                        runBash('su - postgres -c \'psql -c "CREATE DATABASE ' + name + ';" \'').wait()
                                        runBash("su - postgres -c \"psql -c \\\"CREATE USER " + name + " WITH ENCRYPTED PASSWORD '" + password + "';\\\"\"").wait()
                                        runBash('su - postgres -c \'psql -c "GRANT ALL PRIVILEGES ON DATABASE ' + name + ' TO ' + name + ';" \'').wait()
                                    runBash(sudo_cmd + ' bash -c \'umask 006 && source .env/bin/activate && django-admin.py startproject ' + appsname + '\'', cwd=path_virtualhost).wait()
                                    settings = settings.replace('__appname__', appsname)
                                    settings = settings.replace('__virtualhost__', "'" + virtualhost['virtualhost'] + "'")
                                    f = open(path_virtualhost + '/' + appsname + '/' + appsname + '/settings.py', mode='w')
                                    f.write(settings)
                                    f.close()
                                    del settings
                                    runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && python ' + appsname + '/manage.py migrate\'', cwd=path_virtualhost).wait()
                                    runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && python ' + appsname + '/manage.py makemigrations\'', cwd=path_virtualhost).wait()
                                    runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && python ' + appsname + '/manage.py collectstatic --noinput\'', cwd=path_virtualhost).wait()

                                    # if 'djangoSu' in framework:
                                    #     runBash(sudo_cmd + ' bash -c \'source .env/bin/activate && echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser(\'' + framework['djangoSu'] + '\', \'admin@myproject.com\', \'Blueflys1323\')" | python ' + appsname + '/manage.py shell\'', cwd=path_virtualhost).wait()

                                if 'uwsgi_autocreate_config' in framework and framework['uwsgi_autocreate_config'] == 'yes':
                                    appsname = 'website' if not 'app_name' in framework else framework['app_name']
                                    self._cfgSetUwsgiConfigFile(virtualhost=virtualhost['virtualhost'], webhost=webhost['name'], appsname=appsname)
                                if not os.path.exists(self._path_nginx_sites_available + virtualhost['virtualhost'] + '.conf'): self._cfgWebhostSitesDjango(virtualhost=virtualhost['virtualhost'], webhost=webhost['name'], appsname=appsname)
                            elif 'name' in framework and framework['name'] == 'mailpile':
                                self._cfgMailpile()
                        else: # non framework
                            self._cfgWebhostSites(virtualhost=virtualhost['virtualhost'], webhost=webhost['name'], appsname=appsname)
                        if self._certbotGetCertificate(fqdn=virtualhost['virtualhost'], email=self._cfg['letsencrypt']['email']):
                            self._cfgWebhostSitesSsl(virtualhost=virtualhost['virtualhost'])

    def _cfgWebhostSites(self, virtualhost: str = '', webhost: str = '', appsname: str = '', user: str = 'www-data', group: str = 'www-data'):
        f = open('conf/nginx/sites-available/siteDefault.skeleton', mode='r')
        cfg = f.read()
        f.close()
        cfg = cfg.replace('__virtualhost__', virtualhost)
        cfg = cfg.replace('__project_name__', appsname)
        cfg = cfg.replace('__main_folder__', webhost)
        with open(self._path_nginx_sites_available + virtualhost + '.conf', mode='w') as f:
            f.write(cfg)
        os.symlink(self._path_nginx_sites_available + virtualhost + '.conf', self._path_nginx_sites_enabled + virtualhost + '.conf')
        result = subprocess.Popen('nginx -t', shell=True)
        text = result.communicate()[0]
        return_code = result.returncode
        if return_code:
            self._logger.error('nginx configuration is wrongly')
            self._logger.error(text)
            os.remove(self._path_nginx_sites_enabled + virtualhost + '.conf')
            os.remove(self._path_nginx_sites_available + virtualhost + '.conf')
            self._logger.warning('nginx configuration is deleted')
        else:
            runBash('systemctl reload nginx').wait()

    def _cfgWebhostSitesDjango(self, virtualhost: str = '', webhost: str = '', appsname: str = '', user: str = 'www-data', group: str = 'www-data'):
        f = open(self._path_conf + 'nginx/sites-available/siteDjangoDefault.skeleton', mode='r')
        cfg = f.read()
        f.close()
        cfg = cfg.replace('__virtualhost__', virtualhost)
        cfg = cfg.replace('__project_name__', appsname)
        cfg = cfg.replace('__main_folder__', webhost)
        with open(self._path_nginx_sites_available + virtualhost + '.conf', mode='w') as f:
            f.write(cfg)
        os.symlink(self._path_nginx_sites_available + virtualhost + '.conf', self._path_nginx_sites_enabled + virtualhost + '.conf')
        result = subprocess.Popen('nginx -t', shell=True)
        text = result.communicate()[0]
        return_code = result.returncode
        if return_code:
            self._logger.error('nginx configuration is wrongly')
            self._logger.error(text)
            os.remove(self._path_nginx_sites_enabled + virtualhost + '.conf')
            os.remove(self._path_nginx_sites_available + virtualhost + '.conf')
            self._logger.warning('nginx configuration is deleted')
        else:
            runBash('systemctl reload nginx').wait()

    def _cfgWebhostSitesSsl(self, virtualhost: str = ''):
        ssl = f"""
        listen 443 ssl;
        ssl_certificate /etc/letsencrypt/live/{virtualhost}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{virtualhost}/privkey.pem;

        ssl_session_cache shared:le_nginx_SSL:10m;
        ssl_session_timeout 1440m;
        ssl_session_tickets off;

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_prefer_server_ciphers off;

        ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384";

        if ($scheme != "https") {{
            return 301 https://$host$request_uri;
        }}
        """
        with open(self._path_nginx_sites_available + virtualhost + '.conf', mode='r+') as f:
            cfg = f.read()
            newcfg = cfg.replace('#__ssl__#', ssl)
            f.seek(0)
            f.write(newcfg)
            f.truncate()
        result = subprocess.Popen('nginx -t', shell=True)
        text = result.communicate()[0]
        return_code = result.returncode
        if return_code:
            self._logger.error('nginx configuration is wrongly')
            self._logger.error(text)
            with open(self._path_nginx_sites_available + virtualhost + '.conf', mode='w') as f:
                f.write(cfg)
        else:
            runBash('systemctl reload nginx').wait()

    def _cfgSetUwsgiConfigFile(self, virtualhost=str, webhost=str, appsname=str, user='www-data', group='www-data'):
        f = open('conf/uwsgi/uwsgiDefault.ini', mode='r')
        cfg = f.read()
        f.close()
        cfg = cfg.replace('__user__', user)
        cfg = cfg.replace('__group__', group)
        cfg = cfg.replace('__virtualhost__', virtualhost)
        cfg = cfg.replace('__project_name__', appsname)
        cfg = cfg.replace('__main_folder__', webhost)
        filename = virtualhost + '.ini'
        f = open(self._path_uwsgi_config_available + filename, mode='w+')
        f.write(cfg)
        f.close()
        os.symlink(self._path_uwsgi_config_available + filename, self._path_uwsgi_config_enabled + filename)
        if os.path.exists(self._path_conf + 'uwsgi/uwsgi.service'):
            shutil.copyfile(self._path_conf + 'uwsgi/uwsgi.service', '/etc/systemd/system/uwsgi.service')
        runBash('systemctl restart uwsgi').wait()

    def _certbot(self):
        if not 'isCertbotRenewHook' in self._cfg['installSteps']:
            f = open('/etc/letsencrypt/cli.ini', mode='a')
            f.write("\n" + 'renew-by-default = True')
            f.write("\n" + 'renew-hook = systemctl restart nginx postfix dovecot')
            f.close()
            self._cfg['installSteps']['isCertbotRenewHook'] = True

    def _certbotGetCertificate(self, fqdn:str, email: str = '', alias: list = []):
        if not email: email='postmaster@' + fqdn
        if alias: fqdn += ' -d ' + ' -d '.join(alias)
        result = runBash('certbot certonly --non-interactive --agree-tos -m ' + email + ' --no-eff-email --rsa-key-size 4096 --webroot -w /var/www/html -d ' + fqdn)
        text = result.communicate()[0]
        return_code = result.returncode
        if return_code:
            self._logger.error('Certbot failed')
            self._logger.error(return_code + ' ' + text)
            return False
        return True

    def _cfgBashStuff(self):
        self._cfgBashStuffColor('/root/')
        for user in self._cfg['user']:
            self._cfgBashStuffColor(os.path.expanduser('~' + user['name']))

    def _cfgBashStuffColor(self, path:str):
        with open(path + '.bashrc', 'a') as file:
            file.write('printf "\\e[0;37;44m\\]"')
            file.write('setterm --clear=all --background blue\n')
        with open(path + '.bash_logout', 'a') as file:
            file.write('tput reset')

    def _cfgMailServer(self, hostname:str):
        runBash('echo "postfix postfix/mailname string ' + hostname + '" | debconf-set-selections').wait()
        runBash('echo "postfix postfix/main_mailer_type string \'Internet Site\'" | debconf-set-selections').wait()
        self._appsInstaller('mailServer')
        runBash('openssl dhparam -out /etc/ssl/certs/dhparam.pem 2048')
        runBash('groupadd -g 5000 vmail').wait()
        runBash('useradd -g vmail -u 5000 vmail -d /var/vmail').wait()
        runBash('mkdir -p /var/vmail').wait()
        runBash('chown -R vmail:vmail /var/vmail').wait()
        runBash('sudo -Hiu postgres psql -c "CREATE DATABASE postfix;"').wait()
        runBash('sudo -Hiu postgres psql -c "CREATE USER postfix WITH PASSWORD \'mypass\';"').wait()
        runBash('sudo -Hiu postgres psql -c "grant all privileges on database postfix to postfix;"').wait()
        sql = """
            CREATE TABLE domains (
                id serial PRIMARY KEY,
                domain VARCHAR ( 50 ) UNIQUE NOT NULL
            );
            CREATE TABLE users (
                id serial PRIMARY KEY,
                domain_id serial NOT NULL,
                email text UNIQUE NOT NULL,
                password text NOT NULL,
                maildir text NOT NULL,
                created timestamp with time zone DEFAULT now(),
                last_login TIMESTAMP,
                FOREIGN KEY (domain_id)
                    REFERENCES domains (id)
                    ON DELETE CASCADE
            );
            CREATE TABLE alias (
                id serial PRIMARY KEY,
                domain_id serial NOT NULL,
                source VARCHAR ( 100 ) NOT NULL,
                destination VARCHAR ( 100 ) NOT NULL,
                FOREIGN KEY (domain_id)
                    REFERENCES domains (id)
                    ON DELETE CASCADE
            );
        """
        runBash('sudo -Hiu postgres psql postfix -c "' + sql + '"').wait()

    def _cfgMailpile(self):
        # cwd = '/opt/'
        # runBash('git clone --recursive https://github.com/mailpile/Mailpile.git', cwd=cwd).wait()
        # cwd = cwd + 'Mailpile/'
        # runBash('virtualenv -p /usr/bin/python2.7 --system-site-packages mailpile-env', cwd=cwd).wait()
        # runBash('source mailpile-env/bin/activate && pip install -r requirements.txt', cwd=cwd).wait()
        pass

    def _cleanUp(self):
        for file in os.listdir(self._path_nginx_sites_available):
            if file.endswith(".skeleton"):
                os.remove(self._path_nginx_sites_available + file)

    def run(self):
        self._logger.info("Server Setup script started")
        self._parseArgs()
        with open( self._path_conf + 'osCompatibility.yaml', encoding='utf-8') as f:
            osCompatibility = yaml.load(f, Loader=yaml.FullLoader)
        prechecker = preCheck()
        prechecker.check_uid()
        prechecker.is_os_compatible(osCompatibility)
        with open( self._path_conf + 'osApps.yaml', encoding='utf-8') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
            if prechecker._distro[0] in cfg: cfg = cfg[prechecker._distro[0]]
            if str(prechecker._distro[1]) in cfg: self._osApps = cfg[prechecker._distro[1]]
            self._appsInstaller('default')
        self._cfgGetFile()
        self._validateCfg()
        if os.path.exists(self._path_conf + 'network.interface.settings.sh'):
            self._logger.info('Configure network interface')
            runBash('bash ' + self._path_conf + 'network.interface.settings.sh').wait()
        self._cfgGetIpAndSave()
        if 'groups' in self._cfg: self._cfgCreateGroup()
        if 'user' in self._cfg: self._cfgCreateUser()
        else: self._logger.debug('configuration has no user tag')
        self._cfgLocalHostSetup()
        self._firewallSetup()
        if 'ssh' in self._cfg: self._cfgHardnessServer()
        if 'bashStuff' in self._cfg and self._cfg == True: self._cfgBashStuff()
        if 'webserver' in self._cfg: self._cfgWebserver()
        if 'apps' in self._cfg: self._cfgAppsInstall()
        if 'rtmp' in self._cfg: self._cfgRtmpServer()
        if 'webHosts' in self._cfg: self._cfgWebhost()
        if 'mailServer' in self._cfg:
            mailServer = self._cfg['mailServer']
            self._cfgMailServer(mailServer['hostname'])

        self._cleanUp() # TODO

        runBash('systemctl restart nginx').wait()
        runBash('systemctl enable uwsgi').wait()
        runBash('systemctl restart uwsgi').wait()

if __name__ == "__main__":
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
    app = serverSetup()
    app.run()
