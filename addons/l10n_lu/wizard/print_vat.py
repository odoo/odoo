# -*- coding: utf-8 -*-
#Copyright (c) Vincent Cardon <vincent.cardon@tranquil-it-systems.fr>
# Denis Cardon <denis.cardon@tranquilitsystems.com> and Emmanuel RICHARD.
#Ingenieur fondateur
#Tranquil IT Systems

from __future__ import with_statement
from openerp.osv import fields, osv
from openerp import pooler
from openerp import tools
from openerp.tools.translate import _
from openerp.report.render import render
from openerp.report.interface import report_int
from openerp import addons
import tempfile
import os

class external_pdf(render):

    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type='pdf'

    def _render(self):
        return self.pdf


class report_custom(report_int):

    def create(self, cr, uid, ids, datas, context=None):

        pool = pooler.get_pool(cr.dbname)
        taxobj = pool.get('account.tax.code')

        if context is None:
            context = {}
        code_ids = taxobj.search(cr, uid, [('parent_id','child_of',[datas['form']['tax_code_id']])])
        result = {}
        for t in taxobj.browse(cr, uid, code_ids, {'period_id': datas['form']['period_id']}):
            if str(t.code):
                result['case_'+str(t.code)] = '%.2f' % (t.sum_period or 0.0, )
        user = pool.get('res.users').browse(cr, uid, uid, context)

        # Not Clean, to be changed
        partner = user.company_id.partner_id
        result['info_name'] = user.company_id.name
        result['info_vatnum'] = partner.vat
        if partner:
            result['info_address'] = partner.street
            result['info_address2'] = (partner.zip or '') + ' ' + (partner.city or '')
        try:
            tmp_file = tempfile.mkstemp(".pdf")[1]
            try:
                tools.pdf_utils.fill_pdf(addons.get_module_resource('l10n_lu','wizard', '2008_DECL_F_M10.pdf'), tmp_file, result)
                with open(tmp_file, "r") as ofile:
                    self.obj = external_pdf(ofile.read())
            finally:
                try:
                    os.remove(tmp_file)
                except:
                    pass # nothing to do
            self.obj.render()
            return (self.obj.pdf, 'pdf')
        except Exception:
            raise osv.except_osv(_('PDF Not Created!'), _('Please check if package pdftk is installed!'))

report_custom('report.l10n_lu.tax.report.print')

class vat_declaration_report(osv.osv_memory):
    _name = 'vat.declaration.report'
    _description = 'VAT Declaration Report'

    _columns = {
         'tax_code_id': fields.many2one('account.tax.code', 'Company', readonly=False, required=True, domain=[('parent_id','=',False)]),
         'type': fields.selection([('monthly','Monthly'),('quarterly','Quaterly'),('yearly','Yearly')], 'Type', required=True),
         'period_id' : fields.many2one('account.period', 'From Period', required=True),
         'to_period_id': fields.many2one('account.period', 'To Period', required=True),
    }

    _defaults = {
        'type': 'monthly',
    }

    def print_vat_declaration_report(self, cr, uid, ids, context=None):
        active_ids = context.get('active_ids',[])
        data = {}
        data['form'] = {}
        data['ids'] = active_ids
        data['form']['tax_code_id'] = self.browse(cr, uid, ids)[0].tax_code_id.id
        data['form']['period_id'] = self.browse(cr, uid, ids)[0].period_id.id
        return { 'type': 'ir.actions.report.xml', 'report_name': 'l10n_lu.tax.report.print', 'datas': data}

vat_declaration_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
