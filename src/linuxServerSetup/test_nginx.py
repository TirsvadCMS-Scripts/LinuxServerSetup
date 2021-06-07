
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


class runBash(subprocess.Popen):
    # def __init__(self, args, shell=True, stdin=None, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull,"wb"), executable='/bin/bash', cwd=None, **kwargs):
    #     subprocess.Popen.__init__(self, args=args, shell=shell, stdin=stdin, stdout=stdout, stderr=stderr, executable=executable, cwd=cwd, **kwargs)
    def __init__(self, args, shell=True, stdin=None, cwd=None, **kwargs):
        subprocess.Popen.__init__(self, args=args, shell=shell, cwd=cwd, executable='/bin/bash', **kwargs)

def copyTree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copyTree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(s).st_mtime - os.stat(d).st_mtime > 1:
                shutil.copy2(s, d)

class preCheck():
    _logger = logging.getLogger(__name__)
    _distro = distro.linux_distribution(full_distribution_name=False)

    def check_uid(self):
        if not (os.geteuid() == 0):
            if not 'SUDO_UID' in os.environ.keys():
                self._logger.error("This program requires super user priv.")
                # sys.exit(1)

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
    _logger = logging.getLogger(__name__)
    _packageHandler = packageManager()
    _nginx_user = 'www-data'
    _nginx_group = 'www-data'
    _uid: int
    _gid: int
    _osApps: dict

    def init(self, osApps:dict):
        self._logger.info('nginxManager script started')
        self._osApps = osApps

    def _if_not_dir_create(self, path, uid, gid):
        if not os.path.exists(path):
            os.makedirs(path)
        os.chown(path, uid, gid)

    def setUser(self, user:string):
        pass

    def setGroup(self, group:string):
        pass

    def systemctl(self, enable=True, start=True):
        if enable: runBash('systemctl enable nginx').wait()
        if start: runBash('systemctl start nginx').wait()

    def compile(self, nginxVersion: str = '1.19.5', cwd: str = '/root'):
        try:
            pwd.getpwnam(self._nginx_user)
        except KeyError:
            self._logger.debug('groupadd and useradd ' + self._nginx_group + ':' + self._nginx_user)
            runBash('groupadd ' + self._nginx_group).wait()
            runBash('useradd -c "' + self._nginx_user + '" -r -s /sbin/nologin -g ' + self._nginx_group).wait()
        self._logger.info('Installing dependencies for building nginx with hls support')
        if 'nginx' in self._osApps:
            nginx = self._osApps
            print(nginx)

class testNginxManager():
    _logger = logging.getLogger(__name__)
    _path_conf: str
    _cfg: dict
    _osApps: dict
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
    _dbDefault = ''

    def __init__(self):
        self._path_conf = os.path.dirname( os.path.realpath(__file__)) + '/conf/'
        self._file_log = os.path.dirname( os.path.realpath(__file__)) + '/log' + '/main.log'
        with open( self._path_conf + 'osCompatibility.yaml', encoding='utf-8') as f:
            osCompatibility = yaml.load(f, Loader=yaml.FullLoader)
        prechecker = preCheck()
        prechecker.check_uid()
        prechecker.is_os_compatible(osCompatibility)
        with open( self._path_conf + 'osApps.yaml', encoding='utf-8') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
            if prechecker._distro[0] in cfg: cfg = cfg[prechecker._distro[0]]
            if str(prechecker._distro[1]) in cfg: self._osApps = cfg[prechecker._distro[1]]

    def testAppInstall(self):
        pass

    def run(self):
        if 'nginx' in self._osApps: self._osApps = self._osApps['nginx']
        if 'compile' in self._osApps: self._osApps = self._osApps['compile']
        for key in self._osApps:
            self._osApps = self._osApps[key]
        if 'install' in self._osApps:
            print(self._osApps['install'])
        if 'cmd' in self._osApps:
            for item in self._osApps['cmd']:
                print(item)
        if 'compileCmd' in self._osApps:
            for key in self._osApps['compileCmd']:
                print(self._osApps['compileCmd'][key])



if __name__ == "__main__":
    app = testNginxManager()
    app.run()
