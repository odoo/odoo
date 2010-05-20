# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from mx.DateTime import *
import os
import base64
import StringIO

from osv import fields, osv
import tools
import pooler
from report.render import render
from report.interface import report_int

class account_report_print_indicators_with_pdf(osv.osv_memory):
    _name = "account.report.print.indicators.with.pdf"
    _description = "Print Indicators"
    _columns = {
        'file': fields.binary('Select a PDF File', filters='*.pdf', required=True),
        }

    def check_report(self, cr, uid, ids, context=None):
        datas = {}
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
             'ids': context.get('active_ids',[]),
             'model': 'account.report.report',
             'form': data
            }

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'print.indicator.pdf',
            'datas': datas,
            }


account_report_print_indicators_with_pdf()

class external_pdf(render):
        def __init__(self, pdf):
            render.__init__(self)
            self.pdf = pdf
            self.output_type='pdf'
        def _render(self):
            return self.pdf

class report_custom(report_int):
        def create(self, cr, uid, ids, data, context={}):
            pool = pooler.get_pool(cr.dbname)
            obj_indicator = pool.get('account.report.report')
            code_ids = obj_indicator.browse(cr,uid,context['active_id'])

            self.list={}

            def find_child(obj):
                self.list[str(obj.code)]=str(obj.amount)
                if obj.child_ids:
                    for child in obj.child_ids:
                        find_child(child)
                return True

            find_child(code_ids)

            file_contents=base64.decodestring(data['form']['file'])
            fp = StringIO.StringIO(file_contents)

            infile = open(tools.config['addons_path']+"/test.pdf", 'wb')
            infile.write(fp.read())
            infile.close()

            obj_user=pool.get('res.users').browse(cr,uid,uid)
            self.list['printing_user']=str(obj_user.name)
            self.list['company_name']=(obj_user.company_id.name)
            self.list['company_country']=obj_user.company_id.partner_id.country
            self.list['company_vat']=obj_user.company_id.partner_id.vat
            self.list['printing_time']=time.strftime('%H:%M:%S')
            self.list['printing_date']=time.strftime('%D')

            tools.pdf_utils.fill_pdf(tools.config['addons_path']+"/test.pdf",'/tmp/output.pdf',self.list)
            self.obj = external_pdf(file('/tmp/output.pdf').read())
            self.obj.render()
            return (self.obj.pdf, 'pdf')

report_custom('report.print.indicator.pdf')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: