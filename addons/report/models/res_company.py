# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import osv


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

