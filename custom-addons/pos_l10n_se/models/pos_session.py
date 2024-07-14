# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosSession(models.Model):
    _inherit = "pos.session"

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        result["search_params"]["fields"].append("type")
        return result

    def _loader_params_account_tax(self):
        result = super()._loader_params_account_tax()
        result["search_params"]["fields"].append("sweden_identification_letter")
        return result
