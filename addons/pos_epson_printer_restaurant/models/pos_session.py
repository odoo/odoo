# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _meta_restaurant_printer(self):
        meta = super()._meta_restaurant_printer()
        if not meta:
            return
        meta["fields"].append("epson_printer_ip")
        return meta
