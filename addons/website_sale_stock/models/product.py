# -*- coding: utf-8 -*-
from odoo import api, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _product_availabity(self):
        self.ensure_one()
        is_available = True
        if self.type=='product':
            is_available = False
            for route in self.sudo().mapped('route_ids.name'):
                if route in [_("Manufacture"), _("Buy")]:
                    is_available = True
        return is_available
