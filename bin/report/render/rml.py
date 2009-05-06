# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import render
import rml2pdf
import rml2html as htmlizer
import rml2txt as txtizer
import odt2odt as odt
import html2html as html


class rml(render.render):
    def __init__(self, rml, localcontext = None, datas={}, path='.', title=None):
        render.render.__init__(self, datas)
        self.localcontext = localcontext
        self.rml = rml
        self.output_type = 'pdf'
        self.path = path
        self.title=title


    def _render(self):
        return rml2pdf.parseNode(self.rml, self.localcontext, images=self.bin_datas, path=self.path,title=self.title)

class rml2html(render.render):
    def __init__(self, rml,localcontext = None, datas = {}):
        super(rml2html, self).__init__(datas)
        self.rml = rml
        self.localcontext = localcontext
        self.output_type = 'html'

    def _render(self):
        return htmlizer.parseString(self.rml,self.localcontext)

class rml2txt(render.render):
    def __init__(self, xml, datas={}):
        super(rml2txt, self).__init__(datas)
        self.xml = xml
        self.output_type = 'txt'

    def _render(self):
        return txtizer.parseString(self.xml)

class odt2odt(render.render):
    def __init__(self, rml, localcontext = None, datas = {}):
        render.render.__init__(self, datas)
        self.rml_dom = rml
        self.localcontext = localcontext
        self.output_type = 'odt'


    def _render(self):
        return odt.parseNode(self.rml_dom,self.localcontext)

class html2html(render.render):
    def __init__(self, rml, localcontext = None, datas = {}):
        render.render.__init__(self, datas)
        self.rml_dom = rml
        self.localcontext = localcontext
        self.output_type = 'html'
        
    def _render(self):
        return html.parseString(self.rml_dom,self.localcontext)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

