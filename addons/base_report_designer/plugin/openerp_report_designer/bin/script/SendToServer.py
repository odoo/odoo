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
import random
import xmlrpclib
import base64, tempfile
from com.sun.star.task import XJobExecutor
import os
import sys
if __name__<>'package':
    from lib.gui import *
    from lib.error import *
    from lib.functions import *
    from lib.logreport import *
    from lib.tools import *
    from LoginTest import *
    from lib.rpc import *
    database="report"
    uid = 3

class SendtoServer(unohelper.Base, XJobExecutor):
    Kind = {
        'PDF' : 'pdf',
        'OpenOffice': 'sxw',
        'HTML' : 'html'
    }

    def __init__(self, ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        self.logobj=Logger()
        if not loginstatus and __name__=="package":
            exit(1)

        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        desktop=getDesktop()
        oDoc2 = desktop.getCurrentComponent()
        docinfo=oDoc2.getDocumentInfo()

        self.ids = self.sock.execute(database, uid, self.password, 'ir.module.module', 'search', [('name','=','base_report_designer'),('state', '=', 'installed')])
        if not len(self.ids):
            ErrorDialog("Please install base_report_designer module.", "", "Module Uninstalled Error!")
            exit(1)

        report_name = ""
        name=""
        if docinfo.getUserFieldValue(2)<>"" :
            try:
                fields=['name','report_name']
                self.res_other = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'read', [int(docinfo.getUserFieldValue(2))],fields)
                name = self.res_other[0]['name']
                report_name = self.res_other[0]['report_name']
            except:
                import traceback,sys
                info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                self.logob.log_write('ServerParameter', LOG_ERROR, info)
        elif docinfo.getUserFieldValue(3) <> "":
            name = ""
            result =  "rnd"
            for i in range(5):
                result =result + random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890')

            report_name = docinfo.getUserFieldValue(3) + "." + result
        else:
            ErrorDialog("Please select appropriate module...","Note: use OpenERP Report -> Open a new Report", "Module selection ERROR");
            exit(1)

        self.win = DBModalDialog(60, 50, 180, 100, "Send To Server")
        self.win.addFixedText("lblName",10 , 9, 40, 15, "Report Name :")
        self.win.addEdit("txtName", -5, 5, 123, 15,name)
        self.win.addFixedText("lblReportName", 2, 30, 50, 15, "Technical Name :")
        self.win.addEdit("txtReportName", -5, 25, 123, 15,report_name)
        self.win.addCheckBox("chkHeader", 51, 45, 70 ,15, "Corporate Header")
        self.win.setCheckBoxState("chkHeader", True)
        self.win.addFixedText("lblResourceType", 2 , 60, 50, 15, "Select Rpt. Type :")
        self.win.addComboListBox("lstResourceType", -5, 58, 123, 15,True,itemListenerProc=self.lstbox_selected)
        self.lstResourceType = self.win.getControl( "lstResourceType" )
        self.txtReportName=self.win.getControl( "txtReportName" )
        self.txtReportName.Enable=False
        for kind in self.Kind.keys():
            self.lstResourceType.addItem( kind, self.lstResourceType.getItemCount() )

        self.win.addButton( "btnSend", -5, -5, 80, 15, "Send Report to Server", actionListenerProc = self.btnOk_clicked)
        self.win.addButton( "btnCancel", -5 - 80 -5, -5, 40, 15, "Cancel", actionListenerProc = self.btnCancel_clicked)

        self.win.doModalDialog("lstResourceType", self.Kind.keys()[0])

    def lstbox_selected(self, oItemEvent):
        pass

    def btnCancel_clicked(self, oActionEvent):
        self.win.endExecute()

    def btnOk_clicked(self, oActionEvent):
        if self.win.getEditText("txtName") <> "" and self.win.getEditText("txtReportName") <> "":
            desktop=getDesktop()
            oDoc2 = desktop.getCurrentComponent()
            docinfo=oDoc2.getDocumentInfo()
            self.getInverseFieldsRecord(1)
            fp_name = tempfile.mktemp('.'+"sxw")
            if not oDoc2.hasLocation():
                oDoc2.storeAsURL("file://"+fp_name,Array(makePropertyValue("MediaType","application/vnd.sun.xml.writer"),))

            if docinfo.getUserFieldValue(2)=="":
                name=self.win.getEditText("txtName"),
                name_id={}
                try:
                    name_id = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml' , 'search',[('name','=',name)])
                    if not name_id:
                        id=self.getID()
                        docinfo.setUserFieldValue(2,id)
                        rec = {
                                'name': self.win.getEditText("txtReportName"),
                                'key': 'action',
                                'model': docinfo.getUserFieldValue(3),
                                'value': 'ir.actions.report.xml,'+str(id),
                                'key2': 'client_print_multi',
                                'object': True,
                                'user_id': uid
                            }
                        res = self.sock.execute(database, uid, self.password, 'ir.values' , 'create',rec )
                    else :
                        ErrorDialog("This name is already used for another report.\nPlease try with another name.", "", "Error!")
                        self.logobj.log_write('SendToServer',LOG_WARNING, ': report name already used DB %s' % (database))
                        self.win.endExecute()
                except Exception,e:
                    import traceback,sys
                    info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
                    self.logobj.log_write('ServerParameter', LOG_ERROR, info)
            else:

                id = docinfo.getUserFieldValue(2)
                vId = self.sock.execute(database, uid, self.password, 'ir.values' ,  'search', [('value','=','ir.actions.report.xml,'+str(id))])
                rec = { 'name': self.win.getEditText("txtReportName") }
                res = self.sock.execute(database, uid, self.password, 'ir.values' , 'write',vId,rec)
            oDoc2.store()
            data = read_data_from_file( get_absolute_file_path( oDoc2.getURL()[7:] ) )
            self.getInverseFieldsRecord(0)
            #sock = xmlrpclib.ServerProxy(docinfo.getUserFieldValue(0) +'/xmlrpc/object')

            file_type = oDoc2.getURL()[7:].split(".")[-1]
            params = {
                'name': self.win.getEditText("txtName"),
                'model': docinfo.getUserFieldValue(3),
                'report_name': self.win.getEditText("txtReportName"),
                'header': (self.win.getCheckBoxState("chkHeader") <> 0),
                'report_type': self.Kind[self.win.getListBoxSelectedItem("lstResourceType")],
            }
            if self.win.getListBoxSelectedItem("lstResourceType")=='OpenOffice':
                params['report_type']=file_type
            self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'write', int(docinfo.getUserFieldValue(2)), params)
            
            # Call upload_report as the *last* step, as it will call register_all() and cause the report service
            # to be loaded - which requires all the data to be correct in the database
            self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'upload_report', int(docinfo.getUserFieldValue(2)),base64.encodestring(data),file_type,{})

            self.logobj.log_write('SendToServer',LOG_INFO, ':Report %s successfully send using %s'%(params['name'],database))
            self.win.endExecute()
        else:
            ErrorDialog("Either report name or technical name is empty.\nPlease specify an appropriate name.", "", "Error!")
            self.logobj.log_write('SendToServer',LOG_WARNING, ': either report name or technical name is empty.')
            self.win.endExecute()

    def getID(self):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        params = {
            'name': self.win.getEditText("txtName"),
            'model': docinfo.getUserFieldValue(3),
            'report_name': self.win.getEditText('txtReportName')
        }


        id=self.sock.execute(database, uid, self.password, 'ir.actions.report.xml' ,'create', params)
        return id

    def getInverseFieldsRecord(self, nVal):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        count=0
        oParEnum = doc.getTextFields().createEnumeration()
        while oParEnum.hasMoreElements():
            oPar = oParEnum.nextElement()
            if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                oPar.SelectedItem = oPar.Items[nVal]
                if nVal==0:
                    oPar.update()

if __name__<>"package" and __name__=="__main__":
    SendtoServer(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( SendtoServer, "org.openoffice.openerp.report.sendtoserver", ("com.sun.star.task.Job",),)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
