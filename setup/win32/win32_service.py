# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import win32serviceutil
import win32service
import win32api
import win32process
import servicemanager

import sys
import subprocess
import os

try:
    import meta
except ImportError:
    if hasattr(sys, 'frozen'):
        raise
    from setup import generate_files
    generate_files()
    import meta     # noqa

class OpenERPServerService(win32serviceutil.ServiceFramework):
    # required info
    _svc_name_ = meta.nt_service_name
    _svc_display_name_ = "%s %s" % (meta.description, meta.serie)

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # a reference to the server's process
        self.terpprocess = None

    def SvcStop(self):
        # Before we do anything, tell the SCM we are starting the stop process.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        # stop the running OpenERP Server: say it's a normal exit
        win32api.TerminateProcess(int(self.terpprocess._handle), 0)
        servicemanager.LogInfoMsg("OpenERP Server stopped correctly")

    def StartTERP(self):
        # The server finds now its configuration automatically on Windows
        # We start the ERP Server as an independent process, but we keep its handle
        # The server's binary must be one directory above the service's binary (when py2exe'd the python libraries shouldn' mix)
        service_dir = os.path.dirname(sys.argv[0])
        server_dir = os.path.split(service_dir)[0]
        server_path = os.path.join(server_dir, 'server', 'openerp-server.exe')
        self.terpprocess = subprocess.Popen([server_path], cwd=server_dir, creationflags=win32process.CREATE_NO_WINDOW)

    def SvcDoRun(self):
        self.StartTERP()
        servicemanager.LogInfoMsg("OpenERP Server up and running")
        # exit with same exit code as OpenERP process
        sys.exit(self.terpprocess.wait())


def option_handler(opts):
    # configure the service to auto restart on failures...
    subprocess.call(['sc', 'failure', meta.nt_service_name, 'reset=', '0', 'actions=', 'restart/0/restart/0/restart/0'])

if __name__ == '__main__':
    # Do with the service whatever option is passed in the command line
    win32serviceutil.HandleCommandLine(OpenERPServerService, customOptionHandler=option_handler)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
