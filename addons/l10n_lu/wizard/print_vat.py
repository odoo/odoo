# -*- encoding: utf-8 -*-
#Copyright (c) Vincent Cardon <vincent.cardon@tranquil-it-systems.fr>
# Denis Cardon <denis.cardon@tranquilitsystems.com> and Emmanuel RICHARD.
#Ingenieur fondateur
#Tranquil IT Systems


import wizard
import time
import datetime
import pooler
import sys
from mx.DateTime import *
import tools
from report.render import render 
from report.interface import report_int
import os

_tax_form = """<?xml version="1.0"?>
<form string="VAT Legal Declaration">
    <field name="tax_code_id"/>
    <field name="period_id"/>
</form>"""

_tax_fields = {
    'tax_code_id': {
        'string': 'Company',
        'type': 'many2one',
        'relation': 'account.tax.code',
        'required': True,
        'domain': [('parent_id','=',False)]},
    'period_id': {
        'string':'Period',
        'type': 'many2one',
        'relation': 'account.period',
        'required':True
    }
}

class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'
    def _render(self):
        return self.pdf


class report_custom(report_int):
    def create(self, cr, uid, ids, datas, context={}):
        print datas, ids, uid

        taxobj = self.pool.get('account.tax.code')
        code_ids = taxobj.search(cr, uid, [('parent_id','child_of',[datas['form']['tax_code_id']])])
        result = {}
        for t in taxobj.browse(cr, uid, code_ids, {'period_id': datas['form']['period_id']}):
            if t.code:
                result[t.code] = t.sum_period
        os.system('pdftk... output /tmp/tax.pdf')
        self.obj = external_pdf(file('/tmp/tax.pdf').read())
        self.obj.render()

        pdf_string.close()
        return (self.obj.pdf, 'pdf')

report_custom('report.l10n_lu.tax.report.print')


class wizard_report(wizard.interface):
    states = {
        'init': {
             'actions': [],
             'result': {'type':'form', 'arch':_tax_form, 'fields':_tax_fields, 'state':[('end','Cancel'),('pdf','Print Balance Sheet')]},
        },
        'pdf': {
            'actions': [],
            'result': {'type':'print', 'report': 'l10n_lu.tax.report.print', 'state':'end'},
        },
    }
wizard_report('l10n_lu.tax.report.wizard')

