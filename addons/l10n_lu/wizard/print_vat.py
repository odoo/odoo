# -*- coding: utf-8 -*-
#Copyright (c) Vincent Cardon <vincent.cardon@tranquil-it-systems.fr>
# Denis Cardon <denis.cardon@tranquilitsystems.com> and Emmanuel RICHARD.
#Ingenieur fondateur
#Tranquil IT Systems

from __future__ import with_statement
from osv import osv, fields
import pooler
import tools
from tools.translate import _
from report.render import render
from report.interface import report_int
import addons
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
        if partner.address:
            result['info_address'] = partner.address[0].street
            result['info_address2'] = (partner.address[0].zip or '') + ' ' + (partner.address[0].city or '')
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
            raise osv.except_osv(_('pdf not created !'), _('Please check if package pdftk is installed!'))

report_custom('report.l10n_lu.tax.report.print')

class vat_declaration_report(osv.osv_memory):
    _name = 'vat.declaration.report'
    _description = 'VAT Declaration Report'

    _columns = {
         'tax_code_id': fields.many2one('account.tax.code', 'Company', readonly=False, required=True, domain=[('parent_id','=',False)]),
         'period_id' : fields.many2one('account.period', 'Period', required=True)
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
