# -*- coding: utf-8 -*-
from odoo import models, fields, api


class Website(models.Model):
    _inherit = "website"

    @api.multi
    def sale_get_order(self, force_create=False, code=None, update_pricelist=False, force_pricelist=False):
        order = super(Website, self).sale_get_order(force_create, code, update_pricelist, force_pricelist)
        order.recompute_coupon_lines()
        return order
