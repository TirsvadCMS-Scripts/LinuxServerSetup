import os
import subprocess
import logging
import argparse
import pwd

from packageManager.manager import packageManager

class runBash(subprocess.Popen):
    def __init__(self, args, shell=True, stdin=None, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull,"wb"), executable='/bin/bash', cwd=None, **kwargs):
        subprocess.Popen.__init__(self, args=args, shell=shell, stdin=stdin, stdout=stdout, stderr=stderr, executable=executable, cwd=cwd, **kwargs)

class nginx():
    _logger = logging.getLogger(__name__)
    _parser_args = None
    _packageHandler = packageManager()
    _nginx_user = 'www-data'
    _nginx_group = 'www-data'
    _uid: int
    _gid: int

    def __init__(self):
        # self._logger.propagate = False
        self._logger.info('nginx script started')
        if __name__ == "__main__": self._parse_args()
        if self._parser_args is not None and hasattr(self._parser_args, 'nginx_user'): self._nginx_user = self._parser_args.nginx_user
        if self._parser_args is not None and hasattr(self._parser_args, 'nginx_group'): self._nginx_group = self._parser_args.nginx_group
        self._uid = pwd.getpwnam(self._nginx_user).pw_uid
        self._gid = pwd.getpwnam(self._nginx_group).pw_gid
        print(self._nginx_group)

    def _parse_args(self, args=None):
        parser = argparse.ArgumentParser(prog="Nginx web server setup", description='Nginx tool helper')
        parser.add_argument('--nginx-user', type=str, help='Nginx username')
        parser.add_argument('--nginx-group', type=str, help='Nginx groupname')
        self._parser_args = parser.parse_args(args=args)

    def _if_not_dir_create(self, path, uid, gid):
        if not os.path.exists(path):
            os.makedirs(path)
        os.chown(path, uid, gid)

    def compile(self, nginxVersion: str = '1.19.5', cwd: str = '/root'):
        try:
            pwd.getpwnam('www-data')
        except KeyError:
            self._logger.debug('groupadd and useradd www-data')
            runBash('groupadd www-data').wait()
            runBash('useradd -c "www-data" -r -s /sbin/nologin -g www-data').wait()

        self._logger.info('Installing dependencies for building nginx with hls support')
        # ffmpeg package needed by HLS
        if self._packageHandler._distro[0] == 'fedora':
            # self._packageHandler.install('https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm')
            # self._packageHandler.install('https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm')
            # self._packageHandler.install(['ffmpeg', 'ffmpeg-devel'])
            pass
        elif self._packageHandler._distro[0] == 'centos':
            # self._packageHandler.install('https://download.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm')
            # run_bash('dnf config-manager --enable PowerTools', shell=True, stdin=None, stderr=subprocess.STDOUT, executable='/bin/bash').wait()
            # self._packageHandler.install('--nogpgcheck https://download1.rpmfusion.org/free/el/rpmfusion-free-release-8.noarch.rpm')
            # self._packageHandler.install('--nogpgcheck https://download1.rpmfusion.org/nonfree/el/rpmfusion-nonfree-release-8.noarch.rpm')
            # self._packageHandler.install('install_package http://rpmfind.net/linux/epel/7/x86_64/Packages/s/SDL2-2.0.10-1.el7.x86_64.rpm')
            # self._packageHandler.install(['ffmpeg', 'ffmpeg-devel'])
            pass
        else:
            self._packageHandler.install('ffmpeg')

        if self._packageHandler._distro[0] == 'fedora':
            pass
        elif self._packageHandler._distro[0] == 'centos':
            pass
        else:
            # Nginx is a program written in C, so you will first need to install a compiler tools
            self._packageHandler.install(['build-essential', 'git'])
            # Install optional Nginx dependencies
            self._packageHandler.install(['libpcre3', 'libpcre3-dev', 'libssl-dev', 'zlib1g-dev'])

        self._logger.info('Building Nginx version ' + nginxVersion)

        runBash('git clone https://github.com/sergey-dryabzhinsky/nginx-rtmp-module.git', cwd=cwd).wait()
        runBash('curl -s http://nginx.org/download/nginx-' + nginxVersion + '.tar.gz | tar xfz -', cwd=cwd).wait()
        cwd += '/nginx-' + nginxVersion
        cfg = './configure'
        cfg += ' --user=www-data'
        cfg += ' --add-module=../nginx-rtmp-module'
        cfg += ' --with-http_ssl_module'
        cfg += ' --with-http_v2_module'
        cfg += ' --with-file-aio'
        cfg += ' --conf-path=/etc/nginx/nginx.conf'
        cfg += ' --sbin-path=/usr/local/sbin/nginx'
        cfg += ' --pid-path=/run/nginx.pid'
        cfg += ' --error-log-path=/var/log/nginx/error.log'
        cfg += ' --with-threads'
        cfg += ' --http-log-path=/var/log/nginx/access.log'
        runBash(cfg, cwd=cwd).wait()
        runBash('make -s', cwd=cwd).wait()
        runBash('make install', cwd=cwd).wait()

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

    def systemctl(self, enable=True, start=True):
        if enable: runBash('systemctl enable nginx').wait()
        if start: runBash('systemctl start nginx').wait()

    def run(self):
        pass

if __name__ == "__main__":
    chdlr = logging.StreamHandler()
    chdlr.setLevel(logging.INFO)
    chdlr.setFormatter(logging.Formatter('%(name)s - [%(levelname)s]: %(message)s'))
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)',
        handlers=[
            logging.FileHandler(os.path.dirname( os.path.realpath(__file__)) + '/nginx.log', mode='w'),
            chdlr
            ]
    )
    app = nginx()
    app.run()