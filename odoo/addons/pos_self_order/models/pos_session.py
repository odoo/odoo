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

        return sessions

    def _loader_params_product_product(self):
        res = super()._loader_params_product_product()
        res['search_params']['fields'].append('self_order_available')
        return res

    def _pos_data_process(self, loaded_data):
        """
        This is where we need to process the data if we can't do it in the loader/getter
        """
        super()._pos_data_process(loaded_data)
        loaded_data["company_has_self_ordering"] = (
            self.env["pos.config"]
            .sudo()
            .search_count(
                [
                    *self.env["pos.config"]._check_company_domain(self.env.company),
                    '|', ("self_ordering_mode", "=", "kiosk"),
                    ("self_ordering_mode", "=", "mobile"),
                ],
                limit=1,
            )
            > 0
        )
