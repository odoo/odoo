# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import re

from odoo import api, fields, models, _
from odoo.tools import float_compare


_logger = logging.getLogger(__name__)


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'

    so_reference_type = fields.Selection(string='Communication',
        selection=[
            ('so_name', 'Based on Document Reference'),
            ('partner', 'Based on Customer ID')], default='so_name',
        help='You can set here the communication type that will appear on sales orders.'
             'The communication will be given to the customer when they choose the payment method.')


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    sale_order_ids = fields.Many2many('sale.order', 'sale_order_transaction_rel', 'transaction_id', 'sale_order_id',
                                      string='Sales Orders', copy=False, readonly=True)
    sale_order_ids_nbr = fields.Integer(compute='_compute_sale_order_ids_nbr', string='# of Sales Orders')

    def _compute_sale_order_reference(self, order):
        self.ensure_one()
        if self.acquirer_id.so_reference_type == 'so_name':
            return order.name
        else:
            # self.acquirer_id.so_reference_type == 'partner'
            identification_number = order.partner_id.id
            return '%s/%s' % ('CUST', str(identification_number % 97).rjust(2, '0'))

    @api.depends('sale_order_ids')
    def _compute_sale_order_ids_nbr(self):
        for trans in self:
            trans.sale_order_ids_nbr = len(trans.sale_order_ids)

    def _log_payment_transaction_sent(self):
        super(PaymentTransaction, self)._log_payment_transaction_sent()
        for trans in self:
            post_message = trans._get_payment_transaction_sent_message()
            for so in trans.sale_order_ids:
                so.message_post(body=post_message)

    def _log_payment_transaction_received(self):
        super(PaymentTransaction, self)._log_payment_transaction_received()
        for trans in self.filtered(lambda t: t.provider not in ('manual', 'transfer')):
            post_message = trans._get_payment_transaction_received_message()
            for so in trans.sale_order_ids:
                so.message_post(body=post_message)

    def _set_transaction_pending(self):
        # Override of '_set_transaction_pending' in the 'payment' module
        # to sent the quotations automatically.
        super(PaymentTransaction, self)._set_transaction_pending()

        for record in self:
            sales_orders = record.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent'])
            sales_orders.filtered(lambda so: so.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})

            if record.acquirer_id.provider == 'transfer':
                for so in record.sale_order_ids:
                    so.reference = record._compute_sale_order_reference(so)
            # send order confirmation mail
            sales_orders._send_order_confirmation_mail()

    def _check_amount_and_confirm_order(self):
        self.ensure_one()
        for order in self.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent')):
            if float_compare(self.amount, order.amount_total, 2) == 0:
                order.with_context(send_email=True).action_confirm()
            else:
                _logger.warning(
                    '<%s> transaction AMOUNT MISMATCH for order %s (ID %s): expected %r, got %r',
                    self.acquirer_id.provider,order.name, order.id,
                    order.amount_total, self.amount,
                )
                order.message_post(
                    subject=_("Amount Mismatch (%s)") % self.acquirer_id.provider,
                    body=_("The order was not confirmed despite response from the acquirer (%s): order total is %r but acquirer replied with %r.") % (
                        self.acquirer_id.provider,
                        order.amount_total,
                        self.amount,
                    )
                )

    def _set_transaction_authorized(self):
        # Override of '_set_transaction_authorized' in the 'payment' module
        # to confirm the quotations automatically.
        super(PaymentTransaction, self)._set_transaction_authorized()
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state in ('draft', 'sent'))
        for tx in self:
            tx._check_amount_and_confirm_order()

        # send order confirmation mail
        sales_orders._send_order_confirmation_mail()

    def _reconcile_after_transaction_done(self):
        # Override of '_set_transaction_done' in the 'payment' module
        # to confirm the quotations automatically and to generate the invoices if needed.
        sales_orders = self.mapped('sale_order_ids').filtered(lambda so: so.state in ('draft', 'sent'))
        for tx in self:
            tx._check_amount_and_confirm_order()
        # send order confirmation mail
        sales_orders._send_order_confirmation_mail()
        # invoice the sale orders if needed
        self._invoice_sale_orders()
        res = super(PaymentTransaction, self)._reconcile_after_transaction_done()
        if self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice'):
            default_template = self.env['ir.config_parameter'].sudo().get_param('sale.default_email_template')
            if default_template:
                for trans in self.filtered(lambda t: t.sale_order_ids):
                    ctx_company = {'company_id': trans.acquirer_id.company_id.id,
                                   'force_company': trans.acquirer_id.company_id.id,
                                   'mark_invoice_as_sent': True,
                                   }
                    trans = trans.with_context(ctx_company)
                    for invoice in trans.invoice_ids:
                        invoice.message_post_with_template(int(default_template), email_layout_xmlid="mail.mail_notification_paynow")
        return res

    def _invoice_sale_orders(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice'):
            for trans in self.filtered(lambda t: t.sale_order_ids):
                ctx_company = {'company_id': trans.acquirer_id.company_id.id,
                               'force_company': trans.acquirer_id.company_id.id}
                trans = trans.with_context(**ctx_company)
                trans.sale_order_ids._force_lines_to_invoice_policy_order()
                invoices = trans.sale_order_ids._create_invoices()
                trans.invoice_ids = [(6, 0, invoices.ids)]

    @api.model
    def _compute_reference_prefix(self, values):
        prefix = super(PaymentTransaction, self)._compute_reference_prefix(values)
        if not prefix and values and values.get('sale_order_ids'):
            many_list = self.resolve_2many_commands('sale_order_ids', values['sale_order_ids'], fields=['name'])
            return ','.join(dic['name'] for dic in many_list)
        return prefix

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

    def render_sale_button(self, order, submit_txt=None, render_values=None):
        values = {
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
