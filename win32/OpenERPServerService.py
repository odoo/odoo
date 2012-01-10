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

# Win32 python extensions modules
import win32serviceutil
import win32service
import win32event
import win32api
import win32process
import servicemanager

import sys
import subprocess
import os
import thread

class OpenERPServerService(win32serviceutil.ServiceFramework):
    # required info
    _svc_name_ = "openerp-server-6.1"
    _svc_display_name_ = "OpenERP Server 6.1"
    # optionnal info
    _svc_description_ = "OpenERP Server 6.1 service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Create an event which we will use to wait on.
        # The "service stop" request will set this event.
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        # a reference to the server's process
        self.terpprocess = None
        # info if the service terminates correctly or if the server crashed
        self.stopping = False


    def SvcStop(self):
        # Before we do anything, tell the SCM we are starting the stop process.
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        # stop the running TERP Server: say it's a normal exit
        win32api.TerminateProcess(int(self.terpprocess._handle), 0)
        servicemanager.LogInfoMsg("OpenERP Server stopped correctly")
        # And set my event.
        win32event.SetEvent(self.hWaitStop)


    def StartTERP(self):
        # The server finds now its configuration automatically on Windows
        # We start the ERP Server as an independent process, but we keep its handle
        # The server's binary must be one directory above the service's binary (when py2exe'd the python libraries shouldn' mix)
        service_dir = os.path.dirname(sys.argv[0])
        server_dir = os.path.split(service_dir)[0]
        server_path = os.path.join(server_dir, 'server', 'openerp-server.exe')
        self.terpprocess = subprocess.Popen([server_path], cwd=server_dir, creationflags=win32process.CREATE_NO_WINDOW)


    def StartControl(self,ws):
        # this listens to the Service Manager's events
        win32event.WaitForSingleObject(ws, win32event.INFINITE)
        self.stopping = True

    def SvcDoRun(self):
        # Start OpenERP Server itself
        self.StartTERP()
        # start the loop waiting for the Service Manager's stop signal
        thread.start_new_thread(self.StartControl, (self.hWaitStop,))
        # Log a info message that the server is running
        servicemanager.LogInfoMsg("OpenERP Server up and running")
        # verification if the server is really running, else quit with an error
        self.terpprocess.wait()
        if not self.stopping:
            sys.exit("OpenERP Server check: server not running, check the logfile for more info")



if __name__=='__main__':
    # Do with the service whatever option is passed in the command line
    win32serviceutil.HandleCommandLine(OpenERPServerService)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

