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

        pool = pooler.get_pool(cr.dbname)

        taxobj = pool.get('account.tax.code')
        code_ids = taxobj.search(cr, uid, [('parent_id','child_of',[datas['form']['tax_code_id']])])
        result = {}
        for t in taxobj.browse(cr, uid, code_ids, {'period_id': datas['form']['period_id']}):
            if t.code:
                result['case_'+str(t.code)] = '%.2f' % (t.sum_period or 0.0, )

        user = pool.get('res.users').browse(cr, uid, uid, context)

        # Not Clean, to be changed
        partner = user.company_id.partner_id
        result['info_name'] = user.company_id.name
        result['info_vatnum'] = partner.vat
        if partner.address:
            result['info_address'] = partner.address[0].street
            result['info_address2'] = (partner.address[0].zip or '') + ' ' + (partner.address[0].city or '')

        tools.pdf_utils.fill_pdf(tools.config['addons_path']+'/l10n_lu/wizard/2008_DECL_F_M10.pdf', '/tmp/output.pdf', result)
        self.obj = external_pdf(file('/tmp/output.pdf').read())
        self.obj.render()
        return (self.obj.pdf, 'pdf')

report_custom('report.l10n_lu.tax.report.print')


class wizard_report(wizard.interface):
    states = {
        'init': {
             'actions': [],
             'result': {'type':'form', 'arch':_tax_form, 'fields':_tax_fields, 'state':[('end','Cancel'),('pdf','Print Taxes Statement')]},
        },
        'pdf': {
            'actions': [],
            'result': {'type':'print', 'report': 'l10n_lu.tax.report.print', 'state':'end'},
        },
    }
wizard_report('l10n_lu.tax.report.wizard')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
