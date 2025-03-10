# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('config_id', '=', data['pos.config'][0]['id']), ('state', '=', 'opened')]

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
