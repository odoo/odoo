#########################################################################
#
#  Copyright (c) 2003-2004 Danny Brewer d29583@groovegarden.com
#  Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>).
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2.1 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-13017 USA
#
#  See:  http://www.gnu.org/licenses/lgpl.html
#
#############################################################################

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
    from LoginTest import *
    from lib.rpc import *
    database="test"
    uid = 3
#
#
#
# Start OpenOffice.org, listen for connections and open testing document
#
#
class NewReport(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        self.logobj=Logger()
        if not loginstatus and __name__=="package":
            exit(1)
        self.win=DBModalDialog(60, 50, 180, 115, "Open New Report")
        self.win.addFixedText("lblModuleSelection", 2, 2, 60, 15, "Module Selection")
        self.win.addComboListBox("lstModule", -2,13,176,80 , False)
        self.lstModule = self.win.getControl( "lstModule" )
        self.aModuleName=[]
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        ids = self.sock.execute(database, uid, self.password, 'ir.model' , 'search',[])
        fields = [ 'model','name']
        res = self.sock.execute(database, uid, self.password, 'ir.model' , 'read', ids, fields)
        res.sort(lambda x, y: cmp(x['name'],y['name']))

        for i in range(len(res)):
            self.lstModule.addItem(res[i]['name'],self.lstModule.getItemCount())
            self.aModuleName.append(res[i]['model'])
        self.win.addButton('btnOK',-2 ,-5, 70,15,'Use Module in Report' ,actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnCancel',-2 - 70 - 5 ,-5, 35,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        self.win.doModalDialog("",None)

    def btnOk_clicked(self, oActionEvent):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        docinfo.setUserFieldValue(3,self.aModuleName[self.lstModule.getSelectedItemPos()])
        self.logobj.log_write('Module Name',LOG_INFO, ':Module use in creating a report %s  using database %s' % (self.aModuleName[self.lstModule.getSelectedItemPos()], database))
        self.win.endExecute()

    def btnCancel_clicked(self, oActionEvent):
        self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    NewReport(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( \
            NewReport,
            "org.openoffice.openerp.report.opennewreport",
            ("com.sun.star.task.Job",),)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
