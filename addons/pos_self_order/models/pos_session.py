# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('config_id', '=', data['pos.config'][0]['id']), ('state', '=', 'opened')]

    def _load_pos_self_data(self, data):
        result = super()._load_pos_self_data(data)
        if result:
            result[0]['_base_url'] = self.get_base_url()
        return result

    def _post_read_pos_data(self, data):
        data[0]['_self_ordering'] = (
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
        return super()._post_read_pos_data(data)

    @api.autovacuum
    def _gc_session_sequences(self):
        sequences = self.env['ir.sequence'].search([('code', 'ilike', 'pos.order_')])
        session_ids = [int(seq.code.split('_')[-1]) for seq in sequences if seq.code.split('_')[-1].isdigit()]
        session_ids = self.env['pos.session'].search([('id', 'in', session_ids), ('state', '=', 'closed')]).ids
        sequence_to_unlink_ids = sequences.filtered(lambda seq: seq.code in [f'pos.order_{session}' for session in session_ids])
        if sequence_to_unlink_ids:
            sequence_to_unlink_ids.sudo().unlink()
