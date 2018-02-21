# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    @api.multi
    def _set_transaction_pending(self):
        # Override of '_set_transaction_pending' in the 'payment' module
        # to sent the quotations automatically.
        res = super(PaymentTransaction, self)._set_transaction_pending()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'draft')
        sales_orders.force_quotation_send()
        return res

    @api.multi
    def _set_transaction_capture(self):
        # Override of '_set_transaction_capture' in the 'payment' module
        # to confirm the quotations automatically.
        res = super(PaymentTransaction, self)._set_transaction_capture()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'draft')
        sales_orders.force_quotation_send()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'sent')
        sales_orders.action_confirm()
        return res

    @api.multi
    def _set_transaction_posted(self):
        # Override of '_set_transaction_posted' in the 'payment' module
        # to confirm the quotations automatically and to generate the invoices if needed.
        res = super(PaymentTransaction, self)._set_transaction_posted()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'draft')
        sales_orders.force_quotation_send()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state == 'sent')
        sales_orders.action_confirm()

        if not self.env['ir.config_parameter'].sudo().get_param('website_sale.automatic_invoice'):
            return res

        for trans in self.filtered(lambda t: t.sale_order_ids):
            trans.sale_order_ids._force_lines_to_invoice_policy_order()
            invoices = trans.sale_order_ids.action_invoice_create()
            trans.invoice_ids = [(6, 0, invoices)]
        return res

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
        # Not very elegant to do that in this place but this is the only common place in each transaction
        # to log a message in the chatter.
        self._log_payment_transaction_sent()
        return self.acquirer_id.with_context(submit_class='btn btn-primary', submit_txt=submit_txt or _('Pay Now')).sudo().render(
            self.reference,
            order.amount_total,
            order.pricelist_id.currency_id.id,
            values=values,
        )
