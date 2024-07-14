# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import  models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _upsell_context(self):
        context = super()._upsell_context()
        context["skip_procurement"] = True
        return context
