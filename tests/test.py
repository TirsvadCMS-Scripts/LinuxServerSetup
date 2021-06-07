#!/usr/bin/env python3
import sys

sys.path.append('../src/linuxServerSetup')

import pytest
import yaml
from unittest.mock import patch
from linuxServerSetup import serverSetup

class Tests_parser():

    def test_args_help(self):
        app = serverSetup.serverSetup()
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            app._parseArgs(args=['--help'])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        del app

    def test_args_interaction(self):
        app = serverSetup.serverSetup()
        app._parseArgs(['--interaction'])
        del app

    def test_args_verbose(self):
        app = serverSetup.serverSetup()
        app._parseArgs(['--verbose', '3'])
        del app

    def test_args_empty(self):
        app = serverSetup.serverSetup()
        app._parseArgs([])
        del app

class Tests_cfg():
    _app = serverSetup.serverSetup()

    def setup_method(self, test_method):
        # self._app = serverSetup.serverSetup()
        self._app._parseArgs(['--verbose', '3'])
        pass

    def teardown_method(self, test_method):
        pass

    def test_read_cfg_webhost_settigns(self):
        with open('cfg.yaml') as f:
            cfg = yaml.load(f, Loader=yaml.FullLoader)
        self._app.cfg_webhosts_setup(cfg['webHosts'])
        self._app._set_logger()
        self._app._parser_args
