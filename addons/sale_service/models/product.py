# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    project_id = fields.Many2one('project.project', string='Project')
    auto_create_task = fields.Boolean(string='Create Task Automatically', help="Tick this option if you want to create a task automatically each time this product is sold")


class Product(models.Model):
    _inherit = "product.product"

    @api.multi
    def need_procurement(self):
        if self.filtered(lambda product: product.type == 'service' and product.auto_create_task):
            return True
        return super(Product, self).need_procurement()
