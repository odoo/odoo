# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _meta_pos_payment_method(self):
        meta = super()._meta_pos_payment_method()
        meta["fields"].append("six_terminal_ip")
        return meta
