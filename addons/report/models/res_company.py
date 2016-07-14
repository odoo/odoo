# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial
from openerp.osv import osv, fields
from openerp import SUPERUSER_ID

class ResCompany(osv.Model):
    _inherit = 'res.company'

    def _prepare_report_view_action(self, cr, uid, template):
        template_id = self.pool['ir.model.data'].xmlid_to_res_id(cr, uid, template)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.view',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': template_id,
        }

    def edit_external_header(self, cr, uid, ids, context=None):
        return self._prepare_report_view_action(cr, uid, 'report.external_layout_header')

    def edit_external_footer(self, cr, uid, ids, context=None):
        return self._prepare_report_view_action(cr, uid, 'report.external_layout_footer')

    def edit_internal_header(self, cr, uid, ids, context=None):
        return self._prepare_report_view_action(cr, uid, 'report.internal_layout')


class res_company(osv.Model):
    _inherit = 'res.company'

    _columns = {'paperformat_id': fields.many2one('report.paperformat', 'Paper format')}

    def init(self, cr):
        # set a default paperformat based on rml one.
        ref = partial(self.pool['ir.model.data'].xmlid_to_res_id, cr, SUPERUSER_ID)

        ids = self.search(cr, SUPERUSER_ID, [('paperformat_id', '=', False)])
        for company in self.browse(cr, SUPERUSER_ID, ids):
            paperformat_id = {
                'a4': ref('report.paperformat_euro'),
                'us_letter': ref('report.paperformat_us'),
            }.get(company.rml_paper_format) or ref('report.paperformat_euro')

            if paperformat_id:
                company.write({'paperformat_id': paperformat_id})

        sup = super(res_company, self)
        if hasattr(sup, 'init'):
            sup.init(cr)


