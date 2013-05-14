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
import base64, tempfile


from com.sun.star.task import XJobExecutor
import os
import sys
if __name__<>'package':
    from lib.gui import *
    from lib.error import *
    from LoginTest import *
    from lib.logreport import *
    from lib.rpc import *
    database="test"
    uid = 3

class ModifyExistingReport(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"

        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)

        self.win = DBModalDialog(60, 50, 180, 120, "Modify Existing Report")
        self.win.addFixedText("lblReport", 2, 3, 60, 15, "Report Selection")
        self.win.addComboListBox("lstReport", -1,15,178,80 , False )
        self.lstReport = self.win.getControl( "lstReport" )
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo=doc.getDocumentInfo()
        self.logobj=Logger()
        self.hostname = docinfo.getUserFieldValue(0)
        global passwd
        self.password = passwd
        global url
        self.sock=RPCSession(url)
        # Open a new connexion to the server


        ids = self.sock.execute(database, uid, self.password, 'ir.module.module', 'search', [('name','=','base_report_designer'),('state', '=', 'installed')])
        if not len(ids):
            ErrorDialog("Please install base_report_designer module.", "", "Module Uninstalled Error!")
            exit(1)

        ids = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'search', [('report_xsl', '=', False),('report_xml', '=', False)])

        fields=['id', 'name','report_name','model']

        self.reports = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'read', ids, fields)
        self.report_with_id = []

        for report in self.reports:
            if report['name']<>"":
                model_ids = self.sock.execute(database, uid, self.password, 'ir.model' ,  'search', [('model','=', report['model'])])
                model_res_other =self.sock.execute(database, uid, self.password, 'ir.model', 'read', model_ids, [ 'name', 'model' ] )
                if model_res_other <> []:
                    name = model_res_other[0]['name'] + " - " + report['name']
                else:
                    name = report['name'] + " - " + report['model']
                self.report_with_id.append( (report['id'], name, report['model'] ) )

        self.report_with_id.sort( lambda x, y: cmp( x[1], y[1] ) )

        for id, report_name, model_name in self.report_with_id:
            self.lstReport.addItem( report_name, self.lstReport.getItemCount() )

        self.win.addButton('btnSave',10,-5,50,15,'Open Report' ,actionListenerProc = self.btnOk_clicked )
        self.win.addButton('btnCancel',-10 ,-5,50,15,'Cancel' ,actionListenerProc = self.btnCancel_clicked )
        self.win.addButton('btnDelete',15 -80 ,-5,50,15,'Delete Report',actionListenerProc = self.btnDelete_clicked)
        self.win.doModalDialog("lstReport",self.report_with_id[0][1] )

    def btnOk_clicked(self, oActionEvent):
        try:
            desktop=getDesktop()
            doc = desktop.getCurrentComponent()
            docinfo=doc.getDocumentInfo()

            selectedItemPos = self.win.getListBoxSelectedItemPos( "lstReport" )
            id = self.report_with_id[ selectedItemPos ][0]

            res = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'report_get', id)

            if res['file_type'] in ['sxw','odt'] :
               file_type = res['file_type']
            else :
               file_type = 'sxw'

            fp_name = tempfile.mktemp('.'+file_type)
            fp_name1="r"+fp_name
            fp_path=os.path.join(fp_name1).replace("\\","/")
            fp_win=fp_path[1:]

            filename = ( os.name == 'nt' and fp_win or fp_name )
            if res['report_sxw_content']:
                write_data_to_file( filename, base64.decodestring(res['report_sxw_content']))
            url = "file:///%s" % filename

            arr=Array(makePropertyValue("MediaType","application/vnd.sun.xml.writer"),)
            oDoc2 = desktop.loadComponentFromURL(url, "openerp", 55, arr)
            docinfo2=oDoc2.getDocumentInfo()
            docinfo2.setUserFieldValue(0, self.hostname)
            docinfo2.setUserFieldValue(1,self.password)
            docinfo2.setUserFieldValue(2,id)
            docinfo2.setUserFieldValue(3,self.report_with_id[selectedItemPos][2])

            oParEnum = oDoc2.getTextFields().createEnumeration()
            while oParEnum.hasMoreElements():
                oPar = oParEnum.nextElement()
                if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                    oPar.SelectedItem = oPar.Items[0]
                    oPar.update()
            if oDoc2.isModified():
                if oDoc2.hasLocation() and not oDoc2.isReadonly():
                    oDoc2.store()

            ErrorDialog("Download is completed.","Your file has been placed here :\n ."+ fp_name,"Download Message !")
            obj=Logger()
            obj.log_write('Modify Existing Report',LOG_INFO, ':successful download report  %s  using database %s' % (self.report_with_id[selectedItemPos][2], database))
        except Exception, e:
            ErrorDialog("The report could not be downloaded.", "Report: %s\nDetails: %s" % ( fp_name, str(e) ),"Download Message !")
            import traceback,sys
            info = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            self.logobj.log_write('ModifyExistingReport', LOG_ERROR, info)

        self.win.endExecute()

    def btnCancel_clicked(self, oActionEvent):
        self.win.endExecute()

    def btnDelete_clicked(self, oActionEvent):
         desktop=getDesktop()
         doc = desktop.getCurrentComponent()
         docinfo=doc.getDocumentInfo()

         selectedItemPos = self.win.getListBoxSelectedItemPos( "lstReport" )
         name=self.win.getListBoxSelectedItem ("lstReport")
         id = self.report_with_id[ selectedItemPos ][0]
         temp = self.sock.execute(database, uid, self.password, 'ir.actions.report.xml', 'unlink', id,)
         str_value='ir.actions.report.xml,'+str(id)
         ids = self.sock.execute(database, uid, self.password, 'ir.values' ,  'search',[('value','=',str_value)])
         if ids:
            rec = self.sock.execute(database, uid, self.password, 'ir.values', 'unlink', ids,)
         else :
            pass
         if temp:
            ErrorDialog("Report", "The report could not be deleted:\n"+name+".", "Message !")
            self.logobj.log_write('Delete Report', LOG_INFO, ': report %s successfully deleted using database %s.' % (name, database))

         else:
            ErrorDialog("Report", "The report could not be deleted:\n"+name+".", "Message !")
         self.win.endExecute()



if __name__<>"package" and __name__=="__main__":
    ModifyExistingReport(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( ModifyExistingReport, "org.openoffice.openerp.report.modifyreport", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
