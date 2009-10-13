# -*- coding: utf-8 -*-
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

import wizard
import pooler
import time
import datetime
import sys
from mx.DateTime import *
import tools
from report.render import render
from report.interface import report_int
import os
import base64
import StringIO

form = '''<?xml version="1.0"?>
<form string="Print Indicators with PDF">
    <label string="Select the PDF file on which Indicators will be printed."/>
    <newline/>
    <field name="file" colspan="4"/>
</form>'''

fields = {
    'file': {'string':'Select a PDF File', 'type':'binary','required':True,'filters':'*.pdf'},
}


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
        code_ids = obj_indicator.browse(cr,uid,data['id'])

        self.list={}

        def find_child(obj):
            self.list[obj.code]=str(obj.amount)
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
        self.list['printing_user']=obj_user.name
        self.list['company_name']=obj_user.company_id.name
        self.list['company_country']=obj_user.company_id.partner_id.country
        self.list['company_vat']=obj_user.company_id.partner_id.vat
        self.list['printing_time']=time.strftime('%H:%M:%S')
        self.list['printing_date']=time.strftime('%D')

        tools.pdf_utils.fill_pdf(tools.config['addons_path']+"/test.pdf",'/tmp/output.pdf',self.list)
        self.obj = external_pdf(file('/tmp/output.pdf').read())
        self.obj.render()
        return (self.obj.pdf, 'pdf')

report_custom('report.print.indicator.pdf')

class wizard_print_indicators_with_pdf(wizard.interface):
    states = {
        'init': {
            'actions': [],
            'result': {'type': 'form', 'arch':form, 'fields':fields, 'state':[('end','Cancel'),('print','Print')]}
        },
        'print': {
            'actions':[],
            'result' :{'type':'print','report':'print.indicator.pdf', 'state':'end'}
        }
    }
wizard_print_indicators_with_pdf('print.indicators.pdf')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
