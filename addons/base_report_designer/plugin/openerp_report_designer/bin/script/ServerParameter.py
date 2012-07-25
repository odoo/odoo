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
    from Change import *
    database="test"

class ServerParameter( unohelper.Base, XJobExecutor ):
    def __init__(self, aVal= None, sURL=""):
        self.module  = "openerp_report"
        self.version = "0.1"
        desktop=getDesktop()
        log_detail(self)
        self.logobj=Logger()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.win=DBModalDialog(60, 50, 160, 108, "Server Connection Parameter")
        self.win.addFixedText("lblVariable", 2, 12, 35, 15, "Server URL")
        if docinfo.getUserFieldValue(0)=="":
           docinfo.setUserFieldValue(0,"http://localhost:8069")
        self.win.addFixedText("txtHost",-20,12,105,15,sURL)
        self.win.addFixedText("lblDatabaseName", 6, 31, 31, 15, "Database")


        self.win.addFixedText("lblLoginName", 17, 51, 20, 15, "Login")
        self.win.addEdit("txtLoginName",-2,48,123,15,docinfo.getUserFieldValue(1))

        self.win.addFixedText("lblPassword", 6, 70, 31, 15, "Password")
        self.win.addEdit("txtPassword",-2,67,123,15,)
        self.win.setEchoChar("txtPassword",42)


        self.win.addButton('btnOK',-2 ,-5, 60,15,'Connect' ,actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnPrevious',15 -80 ,-5,50,15,'Previous',actionListenerProc = self.btnPrevious_clicked)
        self.win.addButton('btnCancel',-2 - 110 - 5 ,-5, 35,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )
 
        sValue=""
        if docinfo.getUserFieldValue(0)<>"":
            global url
            global result
            url=docinfo.getUserFieldValue(0)
            self.sock=RPCSession(url)
            res=self.sock.listdb()
            result=res
            if res == -1:
                self.win.addEdit("lstDatabase",-2,28,123,15)
#                sValue="Could not connect to the server!"
#                self.lstDatabase.addItem("Could not connect to the server!",0)
            elif res == 0:
                sValue="No Database is found !"
                self.lstDatabase.addItem("No Database is found !",0)
            else:
                self.win.addComboListBox("lstDatabase", -2,28,123,15, True)
                self.lstDatabase = self.win.getControl( "lstDatabase" )
                self.win.removeListBoxItems("lstDatabase", 0, self.win.getListBoxItemCount("lstDatabase"))
                for i in range(len(res)):
                    self.lstDatabase.addItem(res[i],i)
                sValue = database
        if sValue:
            self.win.doModalDialog("lstDatabase",sValue)
        else:
            self.win.doModalDialog("lstDatabase",None)

        #self.win.doModalDialog("lstDatabase",docinfo.getUserFieldValue(2))

    def btnOk_clicked(self,oActionEvent):

        sLogin=self.win.getEditText("txtLoginName")
        sPassword=self.win.getEditText("txtPassword")
        global url
        global result
        if result==-1:
            sDatabase=self.win.getEditText("lstDatabase")
        else:
            sDatabase=self.win.getListBoxSelectedItem("lstDatabase")
        self.sock=RPCSession(url)
        UID = self.sock.login(sDatabase,sLogin,sPassword)
        if not UID or UID==-1 :
            ErrorDialog("Connection Refuse...","Please enter valid Login/Password.")
          #  self.win.endExecute()
        ids_module =self.sock.execute(sDatabase, UID, sPassword, 'ir.module.module', 'search', [('name','=','base_report_designer'),('state', '=', 'installed')])
        if not len(ids_module):
            ErrorDialog("Please install base_report_designer module.", "", "Module Uninstalled Error !")
            self.logobj.log_write('Module is not found.',LOG_WARNING, ':base_report_designer not install in  database %s.' % (sDatabase))
            #self.win.endExecute()
        else:
            desktop=getDesktop()
            doc = desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()
            docinfo.setUserFieldValue(0,self.win.getEditText("txtHost"))
            docinfo.setUserFieldValue(1,self.win.getEditText("txtLoginName"))
            global passwd
            passwd=self.win.getEditText("txtPassword")
            global loginstatus
            loginstatus=True
            global database
            database=sDatabase
            global uid
            uid=UID
            #docinfo.setUserFieldValue(2,self.win.getListBoxSelectedItem("lstDatabase"))
            #docinfo.setUserFieldValue(3,"")

            ErrorDialog(" You can start creating your report in \n  \t the current document.","After Creating  sending to the server.","Message !")
            self.logobj.log_write('successful login',LOG_INFO, ':successful login from %s  using database %s' % (sLogin, sDatabase))
            self.win.endExecute()

      
    def btnCancel_clicked( self, oActionEvent ):
        self.win.endExecute()

    def btnPrevious_clicked(self,oActionEvent):
        self.win.endExecute()
        Change(None)
        self.win.endExecute()
        

if __name__<>"package" and __name__=="__main__":
    ServerParameter(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( ServerParameter, "org.openoffice.openerp.report.serverparam", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
