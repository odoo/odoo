# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _force_http(self):
        if self.payment_method_ids.filtered(lambda pm: pm.use_payment_terminal == 'six'):
            return True
        return super(PosConfig, self)._force_http()
