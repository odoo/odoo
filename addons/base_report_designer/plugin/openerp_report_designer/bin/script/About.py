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
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
#
#  See:  http://www.gnu.org/licenses/lgpl.html
#
#############################################################################

import uno
from com.sun.star.task import XJobExecutor

if __name__<>'package':
    from lib.gui import *

class About(unohelper.Base, XJobExecutor):
    def __init__(self, ctx):
        self.ctx     = ctx
        self.module  = "openerp_report"
        self.version = "0.1"
        self.win = DBModalDialog(60, 50, 175, 115, "About OpenERP Report Designer")

        fdBigFont = createUnoStruct("com.sun.star.awt.FontDescriptor")
        fdBigFont.Width = 20
        fdBigFont.Height = 25
        fdBigFont.Weight = 120
        fdBigFont.Family= 3

        oLabelTitle1 = self.win.addFixedText("lblTitle1", 1, 1, 35, 30)
        oLabelTitle1.Model.TextColor = 16056320
        oLabelTitle1.Model.FontDescriptor = fdBigFont
        oLabelTitle1.Model.FontRelief = 1
        oLabelTitle1.Text = "Open"

        oLabelTitle2 = self.win.addFixedText("lblTitle2", 35, 1, 30, 30)
        oLabelTitle2.Model.TextColor = 1
        oLabelTitle2.Model.FontDescriptor = fdBigFont
        oLabelTitle2.Model.FontRelief = 1
        oLabelTitle2.Text = "ERP"

        oLabelProdDesc = self.win.addFixedText("lblProdDesc", 1, 30, 173, 75)
        oLabelProdDesc.Model.TextColor = 1
        fdBigFont.Width = 10
        fdBigFont.Height = 11
        fdBigFont.Weight = 76
        oLabelProdDesc.Model.FontDescriptor = fdBigFont
        oLabelProdDesc.Model.Align = 1
        oLabelProdDesc.Model.FontRelief = 1
        oLabelProdDesc.Model.MultiLine = True
        oLabelProdDesc.Text = "This  package  helps  you  to  create  or  modify\nreports  in  OpenERP.  Once  connected  to  the\nserver, you can design your template of reports\nusing fields  and expressions  and  browsing the\ncomplete structure of OpenERP object database."

        oLabelFooter = self.win.addFixedText("lblFooter", -1, -1, 173, 25)
        oLabelFooter.Model.TextColor = 255
        #oLabelFooter.Model.BackgroundColor = 1
        oLabelFooter.Model.Border = 2
        oLabelFooter.Model.BorderColor = 255
        fdBigFont.Width = 8
        fdBigFont.Height = 9
        fdBigFont.Weight = 100
        oLabelFooter.Model.FontDescriptor = fdBigFont
        oLabelFooter.Model.Align = 1
        oLabelFooter.Model.FontRelief = 1
        oLabelFooter.Model.MultiLine = True
        sMessage = "OpenERP Report Designer v1.0 \nCopyright 2007-TODAY Tiny sprl \nThis product is free software, under the GNU Affero General Public License."
        oLabelFooter.Text = sMessage

        self.win.doModalDialog("",None)

if __name__<>"package" and __name__=="__main__":
    About(None)
elif __name__=="package":
    g_ImplementationHelper.addImplementation( About, "org.openoffice.openerp.report.about", ("com.sun.star.task.Job",),)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
