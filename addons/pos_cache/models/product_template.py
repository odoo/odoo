# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def unlink(self):
        if self.filtered('available_in_pos'):
            self.env['pos.cache'].search([]).unlink()
        return super(ProductTemplate, self).unlink()
