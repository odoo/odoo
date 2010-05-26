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
		"Field-1 Eg. http://localhost:8069"
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
		"Field-1 Eg. http://localhost:8069 \n"
		"OR \n"
		"Field-4 Eg. account.invoice"
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

