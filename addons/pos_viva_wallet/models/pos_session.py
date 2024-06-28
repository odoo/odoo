# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = 'pos.session'

    def _load_data_params(self, config_id):
        result = super()._load_data_params(config_id)
        result['pos.payment.method']['fields'].append('viva_wallet_terminal_id')
        return result
