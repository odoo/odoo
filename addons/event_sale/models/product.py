# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'


    @api.onchange('detailed_type')
    def _onchange_type_event(self):
        if self.detailed_type == 'event':
            self.invoice_policy = 'order'
