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

import re
import uno
import string
import unohelper
import xmlrpclib
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from Expression import Expression
    from Fields import Fields
    from Repeatln import RepeatIn
    from lib.error import *
    database="test"
    uid = 3

class modify(unohelper.Base, XJobExecutor ):
    def __init__( self, ctx ):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"

        # Variable Declaration
        desktop = getDesktop()
        doc = desktop.getCurrentComponent()
        docinfo = doc.getDocumentInfo()
        self.oVC = doc.CurrentController.getViewCursor()
        if not docinfo.getUserFieldValue(0)=="":
            self.sMyHost= docinfo.getUserFieldValue(0)
        else:
            ErrorDialog(
		"Please insert user define field Field-1",
		"Just go to File->Properties->User Define \n"
		"Field-1 E.g. http://localhost:8069"
	    )
            exit(1)

        # Check weather Field-4 is available or not otherwise exit from application
        if not docinfo.getUserFieldValue(3) == "" and not docinfo.getUserFieldValue(0)=="":
            if self.oVC.TextField:
                self.oCurObj=self.oVC.TextField
		item = self.oCurObj.Items[0]

		kind, group1, group2 = self.getOperation(self.oCurObj.Items[1] )

		start_group1 = group1[:group1.find(".")]
		stop_group1 = group1[group1.find("."):].replace(".", "/")

                if kind == "field":
		    Fields( start_group1, stop_group1, item, True )
                elif kind == "expression":
                    Expression( group1, item, True )
                elif kind == "repeatIn":
		    RepeatIn( start_group1, group2, stop_group1, item, True )
            else:
                ErrorDialog(
		    "Please place your cursor at begaining of field \n"
		    "which you want to modify",""
		)

        else:
            ErrorDialog(
		"Please insert user define field Field-1 or Field-4",
		"Just go to File->Properties->User Define \n"
		"Field-1 E.g. http://localhost:8069 \n"
		"OR \n"
		"Field-4 E.g. account.invoice"
	    )
            exit(1)

    def getOperation(self, str):
        #str = "[[ RepeatIn(objects, 'variable') ]]" #repeatIn
        #str = "[[ saleorder.partner_id.name ]]" # field
        #str = "[[ some thing complex ]]" # expression
        method1 = lambda x: (u'repeatIn', x.group(1), x.group(2))
        method2 = lambda x: (u'field', x.group(1), None)
        method3 = lambda x: (u'expression', x.group(1), None)
        regexes = [
	    ('\\[\\[ *repeatIn\\( *(.+)*, *\'([a-zA-Z0-9_]+)\' *\\) *\\]\\]', method1),
	    ('\\[\\[ *([a-zA-Z0-9_\.]+) *\\]\\]', method2),
	    ('\\[\\[ *(.+) *\\]\\]', method3)
        ]
        for (rule,method) in regexes:
	    res = re.match(rule, str)
	    if res:
		return method(res)

if __name__<>"package":
    modify(None)
else:
    g_ImplementationHelper.addImplementation( modify, "org.openoffice.openerp.report.modify", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
