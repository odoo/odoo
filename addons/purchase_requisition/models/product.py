# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    purchase_requisition_id = fields.Many2one('purchase.requisition', related='purchase_requisition_line_id.requisition_id', string='Agreement', readonly=False)
    purchase_requisition_line_id = fields.Many2one('purchase.requisition.line')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_sellers(self, params):
        sellers = super(ProductProduct, self)._prepare_sellers(params)
        if params and params.get('order_id'):
            return sellers.filtered(lambda s: not s.purchase_requisition_id or s.purchase_requisition_id == params['order_id'].requisition_id)
        else:
            return sellers


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_requisition = fields.Selection(
        [('rfq', 'Create a draft purchase order'),
         ('tenders', 'Propose a call for tenders')],
        string='Procurement', default='rfq',
        help="Create a draft purchase order: Based on your product configuration, the system will create a draft "
             "purchase order.Propose a call for tender : If the 'purchase_requisition' module is installed and this option "
             "is selected, the system will create a draft call for tender.")
