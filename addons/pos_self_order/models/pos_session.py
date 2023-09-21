# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model_create_multi
    def create(self, vals_list):
        sessions = super(PosSession, self).create(vals_list)
        sessions = self._create_pos_self_sessions_sequence(sessions)
        return sessions

    @api.model
    def _create_pos_self_sessions_sequence(self, sessions):
        date_string = fields.Date.today().isoformat()
        ir_sequence = self.env['ir.sequence'].sudo().search([('code', '=', f'pos.order_{date_string}')])
        company_id = self.env.company.id

        for session in sessions:
            session.env['ir.sequence'].sudo().create({
                'name': _("PoS Order by Session"),
                'padding': 4,
                'code': f'pos.order_{session.id}',
                'number_next': 1,
                'number_increment': 1,
                'company_id': company_id,
            })

        if not ir_sequence:
            self.env['ir.sequence'].sudo().create({
                'name': _("PoS Order"),
                'padding': 0,
                'code': f'pos.order_{date_string}',
                'number_next': 1,
                'number_increment': 1,
                'company_id': company_id,
            })

        return sessions

    def _loader_params_product_product(self):
        res = super()._loader_params_product_product()
        res['search_params']['fields'].append('self_order_available')
        return res
