# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import mako
from lxml import etree
from mako.template import Template
from mako.lookup import TemplateLookup
import os

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
        except Exception:
            _logger.exception('report :')

def parseNode(html, localcontext = {}):
    r = makohtml2html(html, localcontext)
    return r.render()
