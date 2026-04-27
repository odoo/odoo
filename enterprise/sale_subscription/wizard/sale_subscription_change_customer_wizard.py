# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaleSubscriptionChangeCustomerWizard(models.TransientModel):
    _name = "sale.subscription.change.customer.wizard"
    _description = 'Subscription Change Customer Wizard'

    partner_id = fields.Many2one("res.partner", string="New Customer")
    partner_invoice_id = fields.Many2one("res.partner", string="New Invoice Address")
    partner_shipping_id = fields.Many2one("res.partner", string="New Delivery Address")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        partner_address_dict = self.partner_id.address_get(['invoice', 'delivery']) if self.partner_id else {}
        self.partner_invoice_id = partner_address_dict.get('invoice', False)
        self.partner_shipping_id = partner_address_dict.get('delivery', False)

    def close(self):
        self.ensure_one()
        sale_orders = self.env['sale.order'].browse(self.env.context.get('active_ids'))
        if not all(sale_orders.mapped('is_subscription')):
            raise UserError(_('You cannot change the customer of non recurring sale order.'))
        sale_orders.write({
            'partner_id': self.partner_id.id,
            'partner_invoice_id': self.partner_invoice_id.id or self.partner_id.id,
            'partner_shipping_id': self.partner_shipping_id.id or self.partner_id.id,
        })
