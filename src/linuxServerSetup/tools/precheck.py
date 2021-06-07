import os
import sys
import distro
import logging

class Precheck():
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