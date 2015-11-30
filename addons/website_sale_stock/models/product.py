# -*- coding: utf-8 -*-
from odoo import api, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.multi
    def _product_availabity(self):
        self.ensure_one()
        if self.type=='product':
            return (True in [(route == _("Make To Order")) for route in self.sudo().mapped('route_ids.name')])
        else:
            return True
