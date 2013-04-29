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
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
#
#  See:  http://www.gnu.org/licenses/lgpl.html
#
#############################################################################

import uno
import unohelper
import string
import re
from com.sun.star.task import XJobExecutor
if __name__<>"package":
    from lib.gui import *
    from LoginTest import *
    database="test"
    uid = 3

class ConvertFieldsToBraces( unohelper.Base, XJobExecutor ):
    def __init__(self, ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        LoginTest()
        if not loginstatus and __name__=="package":
            exit(1)
        self.aReportSyntex=[]
        self.getFields()

    def getFields(self):
        desktop=getDesktop()
        doc = desktop.getCurrentComponent()

        oParEnum = doc.getTextFields().createEnumeration()
        while oParEnum.hasMoreElements():
            oPar = oParEnum.nextElement()
            if oPar.supportsService("com.sun.star.text.TextField.DropDown"):
                oPar.getAnchor().Text.insertString(oPar.getAnchor(),oPar.Items[1],False)
                oPar.dispose()

if __name__<>"package":
    ConvertFieldsToBraces(None)
else:
    g_ImplementationHelper.addImplementation( ConvertFieldsToBraces, "org.openoffice.openerp.report.convertFB", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
