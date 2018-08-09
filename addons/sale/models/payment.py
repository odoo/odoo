# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    sale_order_ids = fields.Many2many('sale.order', 'sale_order_transaction_rel', 'transaction_id', 'sale_order_id',
                                      string='Sales Orders', copy=False, readonly=True)
    sale_order_ids_nbr = fields.Integer(compute='_compute_sale_order_ids_nbr', string='# of Sales Orders')

    @api.depends('sale_order_ids')
    def _compute_sale_order_ids_nbr(self):
        for trans in self:
            trans.sale_order_ids_nbr = len(trans.sale_order_ids)

    @api.multi
    def _log_payment_transaction_sent(self):
        super(PaymentTransaction, self)._log_payment_transaction_sent()
        for trans in self:
            post_message = trans._get_payment_transaction_sent_message()
            for so in trans.sale_order_ids:
                so.message_post(body=post_message)

    @api.multi
    def _log_payment_transaction_received(self):
        super(PaymentTransaction, self)._log_payment_transaction_received()
        for trans in self.filtered(lambda t: t.provider not in ('manual', 'transfer')):
            post_message = trans._get_payment_transaction_received_message()
            for so in trans.sale_order_ids:
                so.message_post(body=post_message)

    @api.multi
    def _set_transaction_pending(self):
        # Override of '_set_transaction_pending' in the 'payment' module
        # to sent the quotations automatically.
        super(PaymentTransaction, self)._set_transaction_pending()

        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'draft')
        sales_orders.force_quotation_send()

    @api.multi
    def _set_transaction_authorized(self):
        # Override of '_set_transaction_authorized' in the 'payment' module
        # to confirm the quotations automatically.
        super(PaymentTransaction, self)._set_transaction_authorized()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'draft')
        sales_orders.force_quotation_send()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'sent')
        for so in sales_orders:
            # For loop because some override of action_confirm are ensure_one.
            so.action_confirm()

    @api.multi
    def _set_transaction_done(self):
        # Override of '_set_transaction_done' in the 'payment' module
        # to confirm the quotations automatically and to generate the invoices if needed.
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'draft')
        sales_orders.force_quotation_send()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'sent')
        sales_orders.action_confirm()

        if self.env['ir.config_parameter'].sudo().get_param('website_sale.automatic_invoice'):
            for trans in self.filtered(lambda t: t.sale_order_ids):
                trans.sale_order_ids._force_lines_to_invoice_policy_order()
                invoices = trans.sale_order_ids.action_invoice_create()
                trans.invoice_ids = [(6, 0, invoices)]
        return super(PaymentTransaction, self)._set_transaction_done()

    @api.model
    def _compute_reference_prefix(self, values):
        prefix = super(PaymentTransaction, self)._compute_reference_prefix(values)
        if not prefix and values and values.get('sale_order_ids'):
            many_list = self.resolve_2many_commands('sale_order_ids', values['sale_order_ids'], fields=['name'])
            return ','.join(dic['name'] for dic in many_list)
        return prefix

    @api.multi
    def action_view_sales_orders(self):
        action = {
            'name': _('Sales Order(s)'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'target': 'current',
        }
        sale_order_ids = self.sale_order_ids.ids
        if len(sale_order_ids) == 1:
            action['res_id'] = sale_order_ids[0]
            action['view_mode'] = 'form'
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', sale_order_ids)]
        return action

    # --------------------------------------------------
    # Tools for payment
    # --------------------------------------------------

    def render_sale_button(self, order, return_url, submit_txt=None, render_values=None):
        values = {
            'return_url': return_url,
            'partner_id': order.partner_shipping_id.id or order.partner_invoice_id.id,
            'billing_partner_id': order.partner_invoice_id.id,
        }
        if render_values:
            values.update(render_values)
        # Not very elegant to do that here but no choice regarding the design.
        self._log_payment_transaction_sent()
        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values=values,
        )
