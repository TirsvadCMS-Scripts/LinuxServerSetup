#!/usr/bin/env python3
import yaml, os, logging, distro, sys

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


class mytest(object):
    _cfg = {}
    _apps: dict = {}
    _path_conf: dict

    def __init__(self):
        self._path_conf = os.path.dirname( os.path.realpath(__file__)) + '/../src/linuxServerSetup/conf' + '/'

    def run(self):
        prechecker = preCheck()
        with open( self._path_conf + 'osApps.yaml', encoding='utf-8') as f:
            self._cfg = yaml.load(f, Loader=yaml.FullLoader)
            if prechecker._distro[0] in self._cfg: cfg = self._cfg[prechecker._distro[0]]
            if str(prechecker._distro[1]) in cfg: self._apps = cfg[prechecker._distro[1]]

        if 'nginx' in self._apps: nginx = self._apps['nginx']
        if 'compile' in nginx: nginx = nginx['compile']
        for nginxVersion in nginx:
            nginx: dict = nginx[nginxVersion]
        if 'cmd' in nginx:
            for item in nginx['cmd']:
                print(item)
        # print(self._apps)



app = mytest()
app.run()
