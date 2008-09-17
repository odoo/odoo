# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 Tiny SPRL (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
##############################################################################
#
# OpenERPServerService.py
#
# Script installing OpenERP as Windows service

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
    _svc_name_ = "openerp-service"
    _svc_display_name_ = "OpenERP Server"
    # optionnal info
    _svc_description_ = "OpenERP Server service"

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
    server_path = os.path.join(server_dir, 'openerp-server.exe')
    self.terpprocess = subprocess.Popen([server_path], \
                                            cwd=server_dir,
                        creationflags=win32process.CREATE_NO_WINDOW)


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

