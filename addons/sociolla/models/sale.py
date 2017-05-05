from datetime import datetime, timedelta
from openerp import SUPERUSER_ID
from openerp import api, fields, models, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError
from openerp.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class SaleOrder(models.Model):
    _inherit = "sale.order"

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')
    price_undiscounted = fields.Monetary(string='Undiscount Amount', store=True, readonly=True, compute='_amount_all', track_visibility='always')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO, add compute discount
        """
        for order in self:
            amount_untaxed = amount_tax = discount_amount = price_undiscounted = 0.0
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                price_undiscounted += line.price_undiscounted
                discount_amount += line.discount_amount

            order.update({
                'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
                'discount_amount': discount_amount,
                'price_undiscounted': price_undiscounted,
            })

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    discount_amount = fields.Monetary(string='Discount Amount', store=True, readonly=True, compute='_compute_amount', track_visibility='always')
    price_undiscounted = fields.Monetary(string='Undiscount Amount', store=True, readonly=True, compute='_compute_amount', track_visibility='always')

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Override base function to add calculation for discount_amount
        """
        for line in self:
            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            price_undiscounted = round(line.product_uom_qty * line.price_unit) 
            discount_amount = price_undiscounted * ((line.discount or 0.0) / 100.0)

            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'discount_amount': discount_amount,
                'price_undiscounted': price_undiscounted,
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

    @api.multi
    def _prepare_invoice_line(self, qty):
        """
        Override base function to set discount account.
        Prepare the dict of values to create the new invoice line for a sales order line.

        :param qty: float quantity to invoice
        """
        
        self.ensure_one()
        discount_account = self.product_id.property_account_sales_discount_id or self.product_id.categ_id.property_account_sales_discount_categ_id
        if discount_account:
            res = super(SaleOrderLine, self)._prepare_invoice_line(qty)
            res['discount_account_id'] = discount_account.id
            res['discount_amount'] = self.discount_amount
            res['price_undiscounted'] = self.price_undiscounted
        else:
            raise UserError(_('Configuration error!\nCould not find any account to create the discount, are you sure you have a chart of account installed?'))
        
        return res
    