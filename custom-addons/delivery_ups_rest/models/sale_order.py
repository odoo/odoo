# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def _create_delivery_line(self, carrier, price_unit):
        res = super(SaleOrder, self)._create_delivery_line(carrier, price_unit)
        if carrier.delivery_type == 'ups_rest' and carrier.ups_bill_my_account:
            res.name = _('[UPS] UPS Billing will remain to the customer')
        return res

    partner_ups_carrier_account = fields.Char(copy=False, compute='_compute_ups_carrier_account', inverse='_inverse_ups_carrier_account', readonly=False, string="UPS account number")
    ups_bill_my_account = fields.Boolean(related='carrier_id.ups_bill_my_account', readonly=True)

    @api.depends('partner_shipping_id')
    def _compute_ups_carrier_account(self):
        for order in self:
            order.partner_ups_carrier_account = order.partner_shipping_id.with_company(order.company_id).property_ups_carrier_account

    def _inverse_ups_carrier_account(self):
        for order in self:
            order.partner_shipping_id.with_company(order.company_id).property_ups_carrier_account = order.partner_ups_carrier_account

    def _action_confirm(self):
        if any(order.carrier_id.ups_bill_my_account and not order.partner_ups_carrier_account for order in self):
            raise UserError(_('You must enter an UPS account number.'))
        return super(SaleOrder, self)._action_confirm()
