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
from mako import exceptions
from tools.translate import _
from osv.osv import except_osv


class l10n_ch_report_webkit_html(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(l10n_ch_report_webkit_html, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,
            'user':self.pool.get("res.users").browse(cr, uid, uid),
            'mod10r': mod10r,
            '_space': self._space,
            '_get_ref': self._get_ref,
            'comma_me': self.comma_me,
            'police_absolute_path': self.police_absolute_path,
            'bvr_absolute_path': self.bvr_absolute_path,
            'headheight': self.headheight
        })

    _compile_get_ref = re.compile('[^0-9]')
    _compile_comma_me = re.compile("^(-?\d+)(\d{3})")
    _compile_check_bvr = re.compile('[0-9][0-9]-[0-9]{3,6}-[0-9]')
    _compile_check_bvr_add_num = re.compile('[0-9]*$')
    
    def set_context(self, objects, data, ids, report_type=None):
        user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid)
        company = user.company_id
        if not company.invoice_only:
            self._check(ids)
        return super(l10n_ch_report_webkit_html, self).set_context(objects, data, ids, report_type=report_type)
    
    def police_absolute_path(self, inner_path) :
        """Will get the ocrb police absolute path"""
        path = addons.get_module_resource(os.path.join('l10n_ch', 'report', inner_path))
        return  path
        
    def bvr_absolute_path(self) :
        """Will get the ocrb police absolute path"""
        path = addons.get_module_resource(os.path.join('l10n_ch', 'report', 'bvr1.jpg'))
        return  path
        
    def headheight(self):
        report_id = self.pool.get('ir.actions.report.xml').search(self.cr, self.uid, [('name','=', 'BVR invoice')])[0]
        report = self.pool.get('ir.actions.report.xml').browse(self.cr, self.uid, report_id)
        return report.webkit_header.margin_top

    def comma_me(self, amount):
        """Fast swiss number formatting"""
        if  isinstance(amount, float):
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
        """Spaces * 5.

        Example:
            >>> self._space('123456789012345')
            '12 34567 89012 345'
        """
        return ''.join([' '[(i - 2) % nbrspc:] + c for i, c in enumerate(nbr)])
      
        
    def _get_ref(self, inv):
        """Retrieve ESR/BVR reference form invoice in order to print it"""
        res = ''
        if inv.partner_bank_id.bvr_adherent_num:
            res = inv.partner_bank_id.bvr_adherent_num
        invoice_number = ''
        if inv.number:
            invoice_number = self._compile_get_ref.sub('', inv.number)
        return mod10r(res + invoice_number.rjust(26-len(res), '0'))
        
    def _check(self, invoice_ids):
        """Check if the invoice is ready to be printed"""
        if not invoice_ids:
            invoice_ids = []
        cursor = self.cr
        pool = self.pool
        invoice_obj = pool.get('account.invoice')
        ids = invoice_ids
        for invoice in invoice_obj.browse(cursor, self.uid, ids):
            invoice_name = "%s %s" %(invoice.name, invoice.number)
            if not invoice.partner_bank_id:
                raise except_osv(_('UserError'),
                        _('No bank specified on invoice:\n%s' %(invoice_name)))
            if not self._compile_check_bvr.match(
                    invoice.partner_bank_id.post_number or ''):
                raise except_osv(_('UserError'),
                        _(('Your bank BVR number should be of the form 0X-XXX-X! '
                          'Please check your company '
                          'information for the invoice:\n%s')
                          %(invoice_name)))
            if invoice.partner_bank_id.bvr_adherent_num \
                    and not self._compile_check_bvr_add_num.match(
                            invoice.partner_bank_id.bvr_adherent_num):
                raise except_osv(_('UserError'),
                        _(('Your bank BVR adherent number must contain only '
                          'digits!\nPlease check your company '
                          'information for the invoice:\n%s') %(invoice_name)))
        return ''

class BVRWebKitParser(webkit_report.WebKitParser):
    
    def setLang(self, lang):
        if not lang:
            lang = 'en_US'
        self.localcontext['lang'] = lang
        
    def formatLang(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False):
        """format using the know cursor, language from localcontext"""
        if digits is None:
            digits = self.parser_instance.get_digits(value)
        if isinstance(value, (str, unicode)) and not value:
            return ''
        pool_lang = self.pool.get('res.lang')
        lang = self.localcontext['lang']

        lang_ids = pool_lang.search(self.parser_instance.cr, self.parser_instance.uid, [('code','=',lang)])[0]
        lang_obj = pool_lang.browse(self.parser_instance.cr, self.parser_instance.uid, lang_ids)

        if date or date_time:
            if not str(value):
                return ''

            date_format = lang_obj.date_format
            parse_format = '%Y-%m-%d'
            if date_time:
                value=value.split('.')[0]
                date_format = date_format + " " + lang_obj.time_format
                parse_format = '%Y-%m-%d %H:%M:%S'
            if not isinstance(value, time.struct_time):
                return time.strftime(date_format, time.strptime(value, parse_format))

            else:
                date = datetime(*value.timetuple()[:6])
            return date.strftime(date_format)

        return lang_obj.format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)
    
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
                _('Please set a header in company settings.')
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
        self.parser_instance.localcontext.update({'setLang':self.setLang})
        self.parser_instance.localcontext.update({'formatLang':self.formatLang})
        css = report_xml.webkit_header.css
        if not css :
            css = ''
        user = self.pool.get('res.users').browse(cursor, uid, uid)
        company = user.company_id
        parse_template = template
        #default_filters=['unicode', 'entity'] can be used to set global filter
        body_mako_tpl = Template(parse_template ,input_encoding='utf-8', output_encoding='utf-8')
        #BVR specific
        bvr_path = addons.get_module_resource(os.path.join('l10n_ch','report','bvr.mako'))
        body_bvr_tpl = Template(file(bvr_path).read(), input_encoding='utf-8', output_encoding='utf-8')

        helper = report_helper.WebKitHelper(cursor, uid, report_xml.id, context)
        ##BVR Specific
        htmls = []
        for obj in objs :
            self.parser_instance.localcontext['objects'] = [obj]
            if not company.bvr_only:
                try:
                    html = body_mako_tpl.render(
                                                helper=helper, 
                                                css=css,
                                                _=self.translate_call,
                                                **self.parser_instance.localcontext
                                                )
                except Exception, e:
                   raise Exception(exceptions.text_error_template().render())
                htmls.append(html)
            if not company.invoice_only:
                try:
                    bvr = body_bvr_tpl.render(
                                        helper=helper, 
                                        css=css,
                                        _=self.translate_call,
                                        **self.parser_instance.localcontext
                                        )
                except Exception, e:
                   raise Exception(exceptions.text_error_template().render())
                htmls.append(bvr)                            
        head_mako_tpl = Template(header, input_encoding='utf-8', output_encoding='utf-8')
        try:
            head = head_mako_tpl.render(
                                        helper=helper, 
                                        css=css,
                                        _debug=False,
                                        _=self.translate_call,
                                        **self.parser_instance.localcontext
                                    )
        except Exception, e:
           raise Exception(exceptions.text_error_template().render())
        foot = False
        if footer and company.invoice_only :
            foot_mako_tpl = Template(footer, input_encoding='utf-8', output_encoding='utf-8')
            try:
                foot = foot_mako_tpl.render(
                                            helper=helper, 
                                            css=css, 
                                            _=self.translate_call,
                                            **self.parser_instance.localcontext
                                            )
            except Exception, e:
               raise Exception(exceptions.text_error_template().render())
        if report_xml.webkit_debug :
            try:
                deb = head_mako_tpl.render(
                                            helper=helper, 
                                            css=css, 
                                            _debug=html,
                                            _=self.translate_call,
                                            **self.parser_instance.localcontext
                                            )
            except Exception, e:
               raise Exception(exceptions.text_error_template().render())
            return (deb, 'html')
        bin = self.get_lib(cursor, uid)
        pdf = self.generate_pdf(bin, report_xml, head, foot, htmls)
        return (pdf, 'pdf')
    

BVRWebKitParser('report.invoice_web_bvr',
               'account.invoice', 
               'addons/l10n_ch/report/report_webkit_html.mako',
               parser=l10n_ch_report_webkit_html)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
