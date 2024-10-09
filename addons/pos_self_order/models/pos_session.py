# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _, fields


class PosSession(models.Model):
    _inherit = ['pos.session']

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('config_id', '=', data['pos.config']['data'][0]['id']), ('state', '=', 'opened')]

    def _load_pos_data(self, data):
        sessions = super()._load_pos_data(data)
        sessions['data'][0]['_self_ordering'] = (
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
        return sessions
