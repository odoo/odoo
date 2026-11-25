# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class SaleOrder(models.Model):
    """ Added product information to the sale order """
    _inherit = 'sale.order'

    product_id = fields.Many2one('product.template',
                                 string="Product",
                                 help="For getting product information "
                                      "on the order")
    seller_id = fields.Many2one('res.partner', readonly=True,
                                string="Seller",
                                help="Seller details",
                                related='product_id.seller_id')
    quantity = fields.Float(related='order_line.product_uom_qty',
                            string="Quantity", help="Getting product quantity",
                            readonly=False)
    qty_delivered = fields.Float(related='order_line.qty_delivered',
                                 string="Quantity Delivered ",
                                 help="Getting delivered quantity",
                                 readonly=False)
    state = fields.Selection(selection_add=[('pending', 'Pending'),
                                            ('approved', 'Approved'),
                                            ('shipped', 'Shipped'),
                                            ('cancel', 'Cancel')],
                             string="state", help="State of the sale order")
    unit_price = fields.Float(related='order_line.price_unit',
                              string="Unit Price",
                              help="Unit price of the product", readonly=False)
    discount = fields.Float(related='order_line.discount', string="Discount",
                            help="Discount applied on the order line",
                            readonly=False)
    subtotal = fields.Monetary(related='order_line.price_subtotal',
                               string="Subtotal",
                               help="Getting subtotal amount", readonly=False)
    create_date = fields.Datetime(string="Create Date",
                                  help="Date of the record creation",
                                  default=fields.Datetime.today(),
                                  readonly=False)
    description = fields.Text(string="Description",
                              help="Adding description on the product")

    def action_confirm(self):
        """ Super sale order confirm function and add to commission based on
            settings commission value"""
        res = super(SaleOrder, self).action_confirm()
        self.state = 'pending'
        for rec in self.order_line:
            if rec.product_id.seller_id.default_commission:
                partner_ids = self.env['res.partner'].search(
                    [('id', '=', rec.product_id.seller_id.id)])
                partner_ids.total_commission = (
                        partner_ids.total_commission + rec.price_subtotal * (
                        rec.product_id.seller_id.default_commission / 100))
                partner_ids.commission = (
                        partner_ids.total_commission + rec.price_subtotal * (
                        rec.product_id.seller_id.default_commission / 100))
            else:
                commission = self.env['ir.config_parameter'].sudo().get_param(
                    'multi_vendor_marketplace.commission')
                commission_value = float(commission)
                partner_ids = self.env['res.partner'].search(
                    [('id', '=', rec.product_id.seller_id.id)])
                partner_ids.total_commission = (
                        partner_ids.total_commission + rec.price_subtotal * (
                        commission_value / 100))
                partner_ids.commission = (
                        partner_ids.total_commission + rec.price_subtotal * (
                        rec.product_id.seller_id.default_commission / 100))
        return res
