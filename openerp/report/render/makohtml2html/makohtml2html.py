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
import logging
import mako
from lxml import etree
from mako.template import Template
from mako.lookup import TemplateLookup
import openerp.netsvc as netsvc
import traceback, sys, os

_logger = logging.getLogger(__name__)

class makohtml2html(object):
    def __init__(self, html, localcontext):
        self.localcontext = localcontext
        self.html = html

    def format_header(self, html):
        head = html.findall('head')
        header = ''
        for node in head:
            header += etree.tostring(node)
        return header

    def format_footer(self, footer):
        html_footer = ''
        for node in footer[0].getchildren():
            html_footer += etree.tostring(node)
        return html_footer

    def format_body(self, html):
        body = html.findall('body')
        body_list = []
        footer =  self.format_footer(body[-1].getchildren())
        for b in body[:-1]:
            body_list.append(etree.tostring(b).replace('\t', '').replace('\n',''))
        html_body ='''
        <script type="text/javascript">

        var indexer = 0;
        var aryTest = %s ;
        function nextData()
            {
            if(indexer < aryTest.length -1)
                {
                indexer += 1;
                document.forms[0].prev.disabled = false;
                document.getElementById("openerp_data").innerHTML=aryTest[indexer];
                document.getElementById("counter").innerHTML= indexer + 1 + ' / ' + aryTest.length;
                }
            else
               {
                document.forms[0].next.disabled = true;
               }
            }
        function prevData()
            {
            if (indexer > 0)
                {
                indexer -= 1;
                document.forms[0].next.disabled = false;
                document.getElementById("openerp_data").innerHTML=aryTest[indexer];
                document.getElementById("counter").innerHTML=  indexer + 1 + ' / ' + aryTest.length;
                }
            else
               {
                document.forms[0].prev.disabled = true;
               }
            }
    </script>
    </head>
    <body>
        <div id="openerp_data">
            %s
        </div>
        <div>
        %s
        </div>
        <br>
        <form>
            <table>
                <tr>
                    <td td align="left">
                        <input name = "prev" type="button" value="Previous" onclick="prevData();">
                    </td>
                    <td>
                        <div id = "counter">%s / %s</div>
                    </td>
                    <td align="right">
                        <input name = "next" type="button" value="Next" onclick="nextData();">
                    </td>
                </tr>
            </table>
        </form>
    </body></html>'''%(body_list,body_list[0],footer,'1',len(body_list))
        return html_body

    def render(self):
        path = os.path.realpath('addons/base/report')
        temp_lookup = TemplateLookup(directories=[path],output_encoding='utf-8', encoding_errors='replace')
        template = Template(self.html, lookup=temp_lookup)
        self.localcontext.update({'css_path':path})
        final_html ='''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
                    <html>'''
        try:
            html = template.render_unicode(**self.localcontext)
            etree_obj = etree.HTML(html)
            final_html += self.format_header(etree_obj)
            final_html += self.format_body(etree_obj)
            return final_html
        except Exception,e:
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            _logger.error('report :\n%s\n%s\n', tb_s, str(e))

def parseNode(html, localcontext = {}):
    r = makohtml2html(html, localcontext)
    return r.render()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
