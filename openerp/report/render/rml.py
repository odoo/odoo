# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import render
import rml2pdf
import rml2html as htmlizer
import rml2txt as txtizer
import odt2odt as odt
import html2html as html
import makohtml2html as makohtml


class rml(render.render):
    def __init__(self, rml, localcontext = None, datas=None, path='.', title=None):
        render.render.__init__(self, datas, path)
        self.localcontext = localcontext
        self.rml = rml
        self.output_type = 'pdf'
        self.title=title


    def _render(self):
        return rml2pdf.parseNode(self.rml, self.localcontext, images=self.bin_datas, path=self.path,title=self.title)

class rml2html(render.render):
    def __init__(self, rml,localcontext = None, datas=None):
        super(rml2html, self).__init__(datas)
        self.rml = rml
        self.localcontext = localcontext
        self.output_type = 'html'

    def _render(self):
        return htmlizer.parseString(self.rml,self.localcontext)

class rml2txt(render.render):
    def __init__(self, rml, localcontext= None, datas=None):
        super(rml2txt, self).__init__(datas)
        self.rml = rml
        self.localcontext = localcontext
        self.output_type = 'txt'

    def _render(self):
        return txtizer.parseString(self.rml, self.localcontext)

class odt2odt(render.render):
    def __init__(self, rml, localcontext=None, datas=None):
        render.render.__init__(self, datas)
        self.rml_dom = rml
        self.localcontext = localcontext
        self.output_type = 'odt'

    def _render(self):
        return odt.parseNode(self.rml_dom,self.localcontext)

class html2html(render.render):
    def __init__(self, rml, localcontext=None, datas=None):
        render.render.__init__(self, datas)
        self.rml_dom = rml
        self.localcontext = localcontext
        self.output_type = 'html'

    def _render(self):
        return html.parseString(self.rml_dom,self.localcontext)

class makohtml2html(render.render):
    def __init__(self, html, localcontext = None):
        render.render.__init__(self)
        self.html = html
        self.localcontext = localcontext
        self.output_type = 'html'

    def _render(self):
        return makohtml.parseNode(self.html,self.localcontext)
