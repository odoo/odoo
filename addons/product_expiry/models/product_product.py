# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Product(models.Model):
    _inherit = "product.product"

    def action_open_quants(self):
        # Override to hide the `removal_date` column if not needed.
        if not any(product.use_expiration_date for product in self):
            self = self.with_context(hide_removal_date=True)
        return super().action_open_quants()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_expiration_date = fields.Boolean(string='Expiration Date',
        help='When this box is ticked, you have the possibility to specify dates to manage'
        ' product expiration, on the product and on the corresponding lot/serial numbers')
    expiration_time = fields.Integer(string='Expiration Time',
        help='Number of days after the receipt of the products (from the vendor'
        ' or in stock after production) after which the goods may become dangerous'
        ' and must not be consumed. It will be computed on the lot/serial number.')
    use_time = fields.Integer(string='Best Before Time',
        help='Number of days before the Expiration Date after which the goods starts'
        ' deteriorating, without being dangerous yet. It will be computed on the lot/serial number.')
    removal_time = fields.Integer(string='Removal Time',
        help='Number of days before the Expiration Date after which the goods'
        ' should be removed from the stock. It will be computed on the lot/serial number.')
    alert_time = fields.Integer(string='Alert Time',
        help='Number of days before the Expiration Date after which an alert should be'
        ' raised on the lot/serial number. It will be computed on the lot/serial number.')
