# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_info_product_product(self):
        meta = super()._loader_info_product_product()
        meta["fields"].append("optional_product_ids")
        return meta
