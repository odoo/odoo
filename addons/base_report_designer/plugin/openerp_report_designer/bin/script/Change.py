##########################################################################
#
# Portions of this file are under the following copyright and license:
#
#
#   Copyright (c) 2003-2004 Danny Brewer 
#   d29583@groovegarden.com 
# 
#   This library is free software; you can redistribute it and/or 
#   modify it under the terms of the GNU Lesser General Public 
#   License as published by the Free Software Foundation; either 
#   version 2.1 of the License, or (at your option) any later version. 
# 
#   This library is distributed in the hope that it will be useful, 
#   but WITHOUT ANY WARRANTY; without even the implied warranty of 
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU 
#   Lesser General Public License for more details. 
# 
#   You should have received a copy of the GNU Lesser General Public 
#   License along with this library; if not, write to the Free Software 
#   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA 
# 
#   See:  http://www.gnu.org/licenses/lgpl.html 
#
# 
# and other portions are under the following copyright and license:
#
#
#    OpenERP, Open Source Management Solution>..
#    Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>). 
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#
##############################################################################
import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from lib.error import ErrorDialog
    from lib.functions import *
    from lib.logreport import *
    from lib.rpc import *
    from ServerParameter import *
    database="test"

class Change( unohelper.Base, XJobExecutor ):
    def __init__(self, ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        desktop=getDesktop()
        log_detail(self)
        self.logobj=Logger()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.protocol = {
            'XML-RPC': 'http://',
            'XML-RPC secure': 'https://',
            'NET-RPC': 'socket://',
        }  
        host=port=protocol=''
        if docinfo.getUserFieldValue(0):
            m = re.match('^(http[s]?://|socket://)([\w.\-]+):(\d{1,5})$',  docinfo.getUserFieldValue(0) or '')
            host = m.group(2)
            port = m.group(3)
            protocol = m.group(1)
        if  protocol:
            for (key, value) in self.protocol.iteritems(): 
                if value==protocol:
                    protocol=key
                    break
        else:
            protocol='XML-RPC'
        self.win=DBModalDialog(60, 50, 120, 90, "Connect to Open ERP Server")

        self.win.addFixedText("lblVariable", 38, 12, 25, 15, "Server  ")
        self.win.addEdit("txtHost",-2,9,60,15, host or 'localhost')

        self.win.addFixedText("lblReportName",45 , 31, 15, 15, "Port  ")
        self.win.addEdit("txtPort",-2,28,60,15, port or "8069")

        self.win.addFixedText("lblLoginName", 2, 51, 60, 15, "Protocol Connection")

        self.win.addComboListBox("lstProtocol", -2, 48, 60, 15, True)
        self.lstProtocol = self.win.getControl( "lstProtocol" )

        self.win.addButton( 'btnNext', -2, -5, 30, 15, 'Next', actionListenerProc = self.btnNext_clicked )

        self.win.addButton( 'btnCancel', -2 - 30 - 5 ,-5, 30, 15, 'Cancel', actionListenerProc = self.btnCancel_clicked )
       
        for i in self.protocol.keys():
            self.lstProtocol.addItem(i,self.lstProtocol.getItemCount() )
        self.win.doModalDialog( "lstProtocol",  protocol)

    def btnNext_clicked(self, oActionEvent):
        global url
        aVal=''
        #aVal= Fetature used 
        try:
            url = self.protocol[self.win.getListBoxSelectedItem("lstProtocol")]+self.win.getEditText("txtHost")+":"+self.win.getEditText("txtPort")
            self.sock=RPCSession(url)
            desktop=getDesktop()
            doc = desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()        
            docinfo.setUserFieldValue(0,url)
            res=self.sock.listdb()
            self.win.endExecute()
            ServerParameter(aVal,url)
        except :
            import traceback,sys 
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ServerParameter', LOG_ERROR, info)     
            ErrorDialog("Connection to server is fail. Please check your Server Parameter.", "", "Error!")
            self.win.endExecute()
                 
    def btnCancel_clicked(self,oActionEvent):
        self.win.endExecute()
        

if __name__<>"package" and __name__=="__main__":
    Change(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( Change, "org.openoffice.openerp.report.change", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
