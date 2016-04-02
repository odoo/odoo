# -*- coding: utf-8 -*-

import servicemanager
import win32api
import win32process
import win32service
import win32serviceutil

import subprocess
import sys
from os.path import dirname, join, split


execfile(join(dirname(__file__), '..', 'server', 'openerp', 'release.py'))


class OdooService(win32serviceutil.ServiceFramework):
    _svc_name_ = nt_service_name
    _svc_display_name_ = "%s %s" % (nt_service_name, serie)

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.odooprocess = None  # Reference to the server's process

    def SvcStop(self):
        # Before we do anything, tell the SCM we are starting the stop process.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        # Stop the running Odoo: say it's a normal exit
        win32api.TerminateProcess(int(self.odooprocess._handle), 0)
        servicemanager.LogInfoMsg("Odoo stopped correctly")

    def SvcDoRun(self):
        # We start Odoo as an independent process, but we keep its handle
        service_dir = dirname(sys.argv[0])
        server_dir = split(service_dir)[0]
        server_path = join(server_dir, 'server', 'openerp-server.exe')
        self.odooprocess = subprocess.Popen(
            [server_path], cwd=server_dir, creationflags=win32process.CREATE_NO_WINDOW
        )
        servicemanager.LogInfoMsg('Odoo up and running')
        # exit with same exit code as Odoo process
        sys.exit(self.odooprocess.wait())


def option_handler(opts):
    # configure the service to auto restart on failures...
    subprocess.call([
        'sc', 'failure', nt_service_name, 'reset=', '0', 'actions=', 'restart/0/restart/0/restart/0'
    ])


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(OdooService, customOptionHandler=option_handler)
