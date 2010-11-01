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

if __name__<>"package":
    from lib.gui import *
    from lib.functions import *
    from lib.rpc import *

class Change:
    def __init__(self, aVal= None, sURL=""):
        self.win=DBModalDialog(60, 50, 120, 90, "Connect to Open ERP Server")

        self.win.addFixedText("lblVariable", 38, 12, 60, 15, "Server")

        self.win.addEdit("txtHost",-2,9,60,15,sURL[sURL.find("/")+2:sURL.rfind(":")])

        self.win.addFixedText("lblReportName",45 , 31, 60, 15, "Port")
        self.win.addEdit("txtPort",-2,28,60,15,sURL[sURL.rfind(":")+1:])

        self.win.addFixedText("lblLoginName", 2, 51, 60, 15, "Protocol Connection")

        self.win.addComboListBox("lstProtocol", -2, 48, 60, 15, True)
        self.lstProtocol = self.win.getControl( "lstProtocol" )

#        self.lstProtocol.addItem( "XML-RPC", 0)
        #self.lstProtocol.addItem( "XML-RPC secure", 1)
        #self.lstProtocol.addItem( "NET-RPC (faster)", 2)

        self.win.addButton( 'btnOK', -2, -5, 30, 15, 'Ok', actionListenerProc = self.btnOk_clicked )

        self.win.addButton( 'btnCancel', -2 - 30 - 5 ,-5, 30, 15, 'Cancel', actionListenerProc = self.btnCancel_clicked )
        self.aVal=aVal
        self.protocol = {
            'XML-RPC': 'http://',
            'XML-RPC secure': 'https://',
            'NET-RPC': 'socket://',
        }
        for i in self.protocol.keys():
            self.lstProtocol.addItem(i,self.lstProtocol.getItemCount() )

        sValue=self.protocol.keys()[0]
        if sURL<>"":
            sValue=self.protocol.keys()[self.protocol.values().index(sURL[:sURL.find("/")+2])]

        self.win.doModalDialog( "lstProtocol", sValue)

    def btnOk_clicked(self,oActionEvent):
        global url
        url = self.protocol[self.win.getListBoxSelectedItem("lstProtocol")]+self.win.getEditText("txtHost")+":"+self.win.getEditText("txtPort")
        self.sock=RPCSession(url)
        docinfo=doc.getDocumentInfo()        
        docinfo.setUserFieldValue(0,url)
        res=self.sock.listdb()
        if res == -1:
            self.aVal.append(url)
        elif res == 0:
            self.aVal.append("No Database found !!!")
        else:
            self.aVal.append(url)
        self.aVal.append(res)
        self.win.endExecute()

    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

