from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class SaleOrder(models.Model):
    _inherit= "sale.order"

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO, add compute discount
        """
        for order in self:
            amount_untaxed = amount_tax = discount_amount = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                discount_amount += line.discount_amount
            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'discount_amount': discount_amount,
            })

class SaleOrderLine(models.Model):
    _inherit="sale.order.line"

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Override base function to add calculation for discount_amount
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            discount_amount = line.price_unit * (line.discount or 0.0) / 100.0
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'discount_amount': discount_amount,
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })