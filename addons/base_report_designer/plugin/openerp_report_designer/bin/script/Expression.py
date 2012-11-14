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
    database="test"
    uid = 3

class Expression(unohelper.Base, XJobExecutor ):
    def __init__(self, sExpression="", sName="", bFromModify=False):
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
        self.win = DBModalDialog(60, 50, 180, 65, "Expression Builder")
        self.win.addFixedText("lblExpression",17 , 10, 35, 15, "Expression :")
        self.win.addEdit("txtExpression", -5, 5, 123, 15)
        self.win.addFixedText("lblName", 2, 30, 50, 15, "Displayed Name :")
        self.win.addEdit("txtName", -5, 25, 123, 15)
        self.win.addButton( "btnOK", -5, -5, 40, 15, "OK", actionListenerProc = self.btnOk_clicked )
        self.win.addButton( "btnCancel", -5 - 40 -5, -5, 40, 15, "Cancel", actionListenerProc = self.btnCancel_clicked )
        self.bModify=bFromModify
        if self.bModify==True:
            self.win.setEditText("txtExpression",sExpression)
            self.win.setEditText("txtName",sName)
        self.win.doModalDialog("",None)


    def btnOk_clicked(self, oActionEvent):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()
        text = doc.Text
        cursor = doc.getCurrentController().getViewCursor()
        if self.bModify==True:
            oCurObj=cursor.TextField
            sKey=u""+self.win.getEditText("txtName")
            sValue=u"[[ " + self.win.getEditText("txtExpression") + " ]]"
            oCurObj.Items = (sKey,sValue)
            oCurObj.update()
            self.win.endExecute()
        else:
            oInputList = doc.createInstance("com.sun.star.text.TextField.DropDown")
            if self.win.getEditText("txtName")!="" and self.win.getEditText("txtExpression")!="":
                sKey=u""+self.win.getEditText("txtName")
                sValue=u"[[ " + self.win.getEditText("txtExpression") + " ]]"
                if cursor.TextTable==None:
                    oInputList.Items = (sKey,sValue)
                    text.insertTextContent(cursor,oInputList,False)
                else:
                    oTable = cursor.TextTable
                    oCurCell = cursor.Cell
                    tableText = oTable.getCellByName( oCurCell.CellName )
                    oInputList.Items = (sKey,sValue)
                    tableText.insertTextContent(cursor,oInputList,False)
                self.win.endExecute()
            else:
                ErrorDialog("Please fill appropriate data in Name field or in Expression field.")

    def btnCancel_clicked(self, oActionEvent):
        self.win.endExecute()

if __name__<>"package" and __name__=="__main__":
    Expression()
elif __name__=="package":
    g_ImplementationHelper.addImplementation( Expression, "org.openoffice.openerp.report.expression", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
