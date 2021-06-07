import sys

sys.path.append('../src/linuxServerSetup')

import pytest
import logging
from linuxServerSetup.install import main as installer
from linuxServerSetup.serverSetup import serverSetup

class Tests_parser():

    def test_args_help(self):
        app = serverSetup()
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            app._parseArgs(args=['--help'])
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        del app

    def test_args_interaction(self):
        app = serverSetup()
        app._parseArgs(['--interaction'])
        del app

    def test_args_verbose(self):
        app = serverSetup()
        app._parseArgs(['--verbose', '3'])
        del app

    def test_args_empty(self):
        app = serverSetup()
        app._parseArgs([])
        del app

class Test_installer():
    _install = installer()

    def setup_method(self, test_method):
        pass

    def teardown_method(self, test_method):
        pass
