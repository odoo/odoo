# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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

import time
from report import report_sxw
from report_webkit import webkit_report
from report_webkit import report_helper 
from osv import osv
from tools import mod10r
import sys
import os
import re
import wizard
import addons
import pooler
from tools.config import config
from mako.template import Template
from tools.translate import _


class l10n_ch_report_webkit_html(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(l10n_ch_report_webkit_html, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr':cr,
            'uid': uid,
            'user':self.pool.get("res.users").browse(cr, uid, uid),
            'mod10r': mod10r,
            '_space': self._space,
            '_get_ref': self._get_ref,
            'comma_me': self.comma_me,
            'police_absolute_path' : self.police_absolute_path,
            'bvr_absolute_path':self.bvr_absolute_path,
            '_check' : self._check,
            'headheight': self.headheight
        })

    _compile_get_ref = re.compile('[^0-9]')
    _compile_comma_me = re.compile("^(-?\d+)(\d{3})")
    _compile_check_bvr = re.compile('[0-9][0-9]-[0-9]{3,6}-[0-9]')
    _compile_check_bvr_add_num = re.compile('[0-9]*$')

    def police_absolute_path(self, inner_path) :
        """Will get the ocrb police absolute path"""
        path = addons.get_module_resource(os.path.join('l10n_ch','report',inner_path))
        return  path
        
    def bvr_absolute_path(self) :
        """Will get the ocrb police absolute path"""
        path = addons.get_module_resource(os.path.join('l10n_ch','report','bvr1.jpg'))
        return  path
        
    def headheight(self):
        report_id = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid, [('name','=', 'BVR invoice')])[0]
        report = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid, report_id)
        return report.webkit_header.margin_top

    def comma_me(self, amount):
        """Fast swiss number formatting"""
        if  type(amount) is float :
            amount = str('%.2f'%amount)
        else :
            amount = str(amount)
        orig = amount
        new = self._compile_comma_me.sub("\g<1>'\g<2>", amount)
        if orig == new:
            return new
        else:
            return self.comma_me(new)

    def _space(self, nbr, nbrspc=5):
        """Spaces * 5"""
        res = ''
        for i in range(len(nbr)):
            res = res + nbr[i]
            if not (i-1) % nbrspc:
                res = res + ' '
        return res

    def _get_ref(self, inv):
        """Retrieve ESR/BVR reference form invoice in order to print it"""
        res = ''
        if inv.partner_bank_id.bvr_adherent_num:
            res = inv.partner_bank_id.bvr_adherent_num
        invoice_number = ''
        if inv.number:
            invoice_number = self._compile_get_ref.sub('', inv.number)
        return mod10r(res + invoice_number.rjust(26-len(res), '0'))
        
    def _check(self, invoices):
        """Check if the invoice is ready to be printed"""
        cursor = self.cr
        pool = self.pool
        invoice_obj = pool.get('account.invoice')
        ids = [x.id for x in invoices]
        for invoice in invoice_obj.browse(cursor, self.uid, ids):
            if not invoice.partner_bank_id:
                raise wizard.except_wizard(_('UserError'),
                        _('No bank specified on invoice:\n' + \
                                invoice_obj.name_get(cursor, self.uid, [invoice.id],
                                    context={})[0][1]))
            if not self._compile_check_bvr.match(
                    invoice.partner_bank_id.post_number or ''):
                raise wizard.except_wizard(_('UserError'),
                        _("Your bank BVR number should be of the form 0X-XXX-X! " +
                                'Please check your company ' +
                                'information for the invoice:\n' + 
                                invoice_obj.name_get(cursor, self.uid, [invoice.id],
                                    context={})[0][1]))
            if invoice.partner_bank_id.bvr_adherent_num \
                    and not self._compile_check_bvr_add_num.match(
                            invoice.partner_bank_id.bvr_adherent_num):
                raise wizard.except_wizard('UserError',
                        'Your bank BVR adherent number must contain exactly seven' +
                                'digits!\nPlease check your company ' +
                                'information for the invoice:\n' +
                                invoice_obj.name_get(cursor, self.uid, [invoice.id],
                                    context={})[0][1])
        return ""

class BVRWebKitParser(webkit_report.WebKitParser):
    
    def create_single_pdf(self, cursor, uid, ids, data, report_xml, context=None):
        """generate the PDF"""
        self.parser_instance = self.parser(
                                            cursor, 
                                            uid, 
                                            self.name2, 
                                            context=context
                                        )
        self.pool = pooler.get_pool(cursor.dbname)
        objs = self.getObjects(cursor, uid, ids, context)
        self.parser_instance.set_context(objs, data, ids, report_xml.report_type)
        template =  False
        if report_xml.report_file :
            path = addons.get_module_resource(report_xml.report_file)
            if os.path.exists(path) :
                template = file(path).read()
        if not template and report_xml.report_webkit_data :
            template =  report_xml.report_webkit_data
        if not template :
            raise except_osv(_('Webkit Report template not found !'), _(''))
        header = report_xml.webkit_header.html
        footer = report_xml.webkit_header.footer_html
        if not header and report_xml.header:
          raise except_osv(
                _('No header defined for this Webkit report!'),
                _('Please set a header in company settings')
            )
        if not report_xml.header :
            #I know it could be cleaner ...
            header = u"""
<html>
    <head>
        <style type="text/css"> 
            ${css}
        </style>
        <script>
        function subst() {
           var vars={};
           var x=document.location.search.substring(1).split('&');
           for(var i in x) {var z=x[i].split('=',2);vars[z[0]] = unescape(z[1]);}
           var x=['frompage','topage','page','webpage','section','subsection','subsubsection'];
           for(var i in x) {
             var y = document.getElementsByClassName(x[i]);
             for(var j=0; j<y.length; ++j) y[j].textContent = vars[x[i]];
           }
         }
        </script>
    </head>
<body style="border:0; margin: 0;" onload="subst()">
</body>
</html>"""
        css = report_xml.webkit_header.css
        if not css :
            css = ''
        user = self.pool.get('res.users').browse(cursor, uid, uid)
        company= user.company_id
        parse_template = template
        #default_filters=['unicode', 'entity'] can be used to set global filter
        body_mako_tpl = Template(parse_template ,input_encoding='utf-8')
        #BVR specific
        bvr_path = addons.get_module_resource(os.path.join('l10n_ch','report','bvr.mako'))
        body_bvr_tpl = Template(file(bvr_path).read(), input_encoding='utf-8')

        helper = report_helper.WebKitHelper(cursor, uid, report_xml.id, context)
        ##BVR Specific
        htmls = []
        for obj in objs :
            
            self.parser_instance.localcontext['objects'] = [obj]
            if not company.bvr_only:
                html = body_mako_tpl.render(
                                            helper=helper, 
                                            css=css,
                                            _=self.translate_call,
                                            **self.parser_instance.localcontext
                                            )
                htmls.append(html)
            if not company.invoice_only:
                bvr = body_bvr_tpl.render(
                                    helper=helper, 
                                    css=css,
                                    _=self.translate_call,
                                    **self.parser_instance.localcontext
                                    )
                htmls.append(bvr)                            
        head_mako_tpl = Template(header, input_encoding='utf-8')
        head = head_mako_tpl.render(
                                    company=company, 
                                    time=time, 
                                    helper=helper, 
                                    css=css,
                                    formatLang=self.parser_instance.formatLang,
                                    setLang=self.parser_instance.setLang, 
                                    _debug=False
                                )
        foot = False
        if footer and company.invoice_only :
            foot_mako_tpl = Template(footer ,input_encoding='utf-8')
            foot = foot_mako_tpl.render(
                                        company=company, 
                                        time=time, 
                                        helper=helper, 
                                        css=css, 
                                        formatLang=self.parser_instance.formatLang,
                                        setLang=self.parser_instance.setLang,
                                        _=self.translate_call,

                                        )
        if report_xml.webkit_debug :
            deb = head_mako_tpl.render(
                                        company=company, 
                                        time=time, 
                                        helper=helper, 
                                        css=css, 
                                        _debug=html,
                                        formatLang=self.parser_instance.formatLang,
                                        setLang=self.parser_instance.setLang,
                                        _=self.translate_call,
                                        )
            return (deb, 'html')
        bin = self.get_lib(cursor, uid, company.id)
        pdf = self.generate_pdf(bin, report_xml, head, foot, htmls)
        return (pdf, 'pdf')
    

BVRWebKitParser('report.invoice_web_bvr',
               'account.invoice', 
               'addons/l10n_ch/report/report_webkit_html.mako',
               parser=l10n_ch_report_webkit_html)
