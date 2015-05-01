# -*- coding: utf-8 -*-
from openerp import api, fields, models

class Website(models.Model):
    _inherit = 'website'

    stock_warning_active =  fields.Boolean(compute="_compute_options", string='Out of Stock Warning')

    @api.multi
    def _compute_options(self):
        self.stock_warning_active = self.env.ref('website_sale_stock.products_out_of_stock_warning').active
