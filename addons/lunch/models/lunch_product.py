# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

from odoo.addons import decimal_precision as dp
from odoo.osv import expression


class LunchProductCategory(models.Model):
    """ Category of the product such as pizza, sandwich, pasta, chinese, burger... """
    _name = 'lunch.product.category'
    _description = 'Lunch Product Category'

    name = fields.Char('Product Category', required=True)


class LunchProduct(models.Model):
    """ Products available to order. A product is linked to a specific vendor. """
    _name = 'lunch.product'
    _description = 'Lunch Product'

    name = fields.Char('Product', required=True)
    category_id = fields.Many2one('lunch.product.category', 'Product Category', required=True)
    description = fields.Text('Description')
    price = fields.Float('Price', digits=dp.get_precision('Account'))
    supplier = fields.Many2one('res.partner', 'Vendor')
    active = fields.Boolean(default=True)
    available = fields.Boolean(compute='_get_available_product', search='_search_available_products')

    @api.depends('supplier')
    def _get_available_product(self):
        for product in self:
            if not product.supplier:
                product.available = True
            else:
                alerts = self.env['lunch.alert'].search([
                    ('partner_id', '=', self.supplier.id)
                ])
                if alerts and not any(alert.display for alert in alerts):
                    # every alert is not available
                    product.available = False
                else:
                    # no alert for the supplier or at least one is not available
                    product.available = True

    def _search_available_products(self, operator, value):
        alerts = self.env['lunch.alert'].search([])
        supplier_w_alerts = alerts.mapped('partner_id')
        available_suppliers = alerts.filtered(lambda a: a.display).mapped('partner_id')
        available_products = self.search([
            '|',
                ('supplier', 'not in', supplier_w_alerts.ids),
                ('supplier', 'in', available_suppliers.ids)
        ])

        if (operator in expression.NEGATIVE_TERM_OPERATORS and value) or \
           (operator not in expression.NEGATIVE_TERM_OPERATORS and not value):
            # e.g. (available = False) or (available != True)
            return [('id', 'not in', available_products.ids)]
        else:
            # e.g. (available = True) or (available != False)
            return [('id', 'in', available_products.ids)]
