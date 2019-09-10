# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

import render

from cStringIO import StringIO
import xml.dom.minidom

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4
import reportlab.lib

import copy

class simple(render.render):
    def _render(self):
        self.result = StringIO()
        parser = xml.dom.minidom.parseString(self.xml)

        title = parser.documentElement.tagName
        doc = SimpleDocTemplate(self.result, pagesize=A4, title=title,
          author='Odoo, Fabien Pinckaers', leftmargin=10*mm, rightmargin=10*mm)

        styles = reportlab.lib.styles.getSampleStyleSheet()
        title_style = copy.deepcopy(styles["Heading1"])
        title_style.alignment = reportlab.lib.enums.TA_CENTER
        story = [ Paragraph(title, title_style) ]
        style_level = {}
        nodes = [ (parser.documentElement,0) ]
        while len(nodes):
            node = nodes.pop(0)
            value = ''
            n=len(node[0].childNodes)-1
            while n>=0:
                if node[0].childNodes[n].nodeType==3:
                    value += node[0].childNodes[n].nodeValue
                else:
                    nodes.insert( 0, (node[0].childNodes[n], node[1]+1) )
                n-=1
            if not node[1] in style_level:
                style = copy.deepcopy(styles["Normal"])
                style.leftIndent=node[1]*6*mm
                style.firstLineIndent=-3*mm
                style_level[node[1]] = style
            story.append( Paragraph('<b>%s</b>: %s' % (node[0].tagName, value), style_level[node[1]]))
        doc.build(story)
        return self.result.getvalue()

if __name__=='__main__':
    s = simple()
    s.xml = '''<test>
        <author-list>
            <author>
                <name>Fabien Pinckaers</name>
                <age>23</age>
            </author>
            <author>
                <name>Michel Pinckaers</name>
                <age>53</age>
            </author>
            No other
        </author-list>
    </test>'''
    if s.render():
        print s.get()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

