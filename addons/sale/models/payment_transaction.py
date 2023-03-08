# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from datetime import datetime
from dateutil import relativedelta

from odoo import _, api, Command, fields, models, SUPERUSER_ID
from odoo.tools import format_amount, str2bool

_logger = logging.getLogger(__name__)


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    sale_order_ids = fields.Many2many('sale.order', 'sale_order_transaction_rel', 'transaction_id', 'sale_order_id',
                                      string='Sales Orders', copy=False, readonly=True)
    sale_order_ids_nbr = fields.Integer(compute='_compute_sale_order_ids_nbr', string='# of Sales Orders')

    def _compute_sale_order_reference(self, order):
        self.ensure_one()
        if self.provider_id.so_reference_type == 'so_name':
            return order.name
        else:
            # self.provider_id.so_reference_type == 'partner'
            identification_number = order.partner_id.id
            return '%s/%s' % ('CUST', str(identification_number % 97).rjust(2, '0'))

    @api.depends('sale_order_ids')
    def _compute_sale_order_ids_nbr(self):
        for trans in self:
            trans.sale_order_ids_nbr = len(trans.sale_order_ids)

    def _set_pending(self, state_message=None, **kwargs):
        """ Override of `payment` to send the quotations automatically.

        :param str state_message: The reason for which the transaction is set in 'pending' state.
        :return: updated transactions.
        :rtype: `payment.transaction` recordset.
        """
        txs_to_process = super()._set_pending(state_message=state_message, **kwargs)

        for tx in txs_to_process:  # Consider only transactions that are indeed set pending.
            sales_orders = tx.sale_order_ids.filtered(lambda so: so.state in ['draft', 'sent'])
            sales_orders.filtered(
                lambda so: so.state == 'draft'
            ).with_context(tracking_disable=True).action_quotation_sent()

            if tx.provider_id.code == 'custom':
                for so in tx.sale_order_ids:
                    so.reference = tx._compute_sale_order_reference(so)
            # send order confirmation mail.
            sales_orders._send_order_confirmation_mail()

        return txs_to_process

    def _check_amount_and_confirm_order(self):
        """ Confirm the sales order based on the amount of a transaction.

        Confirm the sales orders only if the transaction amount is equal to the total amount of the
        sales orders. Neither partial payments nor grouped payments (paying multiple sales orders in
        one transaction) are not supported.

        :return: The confirmed sales orders.
        :rtype: a `sale.order` recordset
        """
        confirmed_orders = self.env['sale.order']
        for tx in self:
            # We only support the flow where exactly one quotation is linked to a transaction and
            # vice versa.
            if len(tx.sale_order_ids) == 1:
                quotation = tx.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent'))
                if quotation and len(quotation.transaction_ids.filtered(
                    lambda tx: tx.state in ('authorized', 'done')  # Only consider confirmed tx
                )) == 1:
                    # Check if the SO is fully paid
                    if quotation.currency_id.compare_amounts(tx.amount, quotation.amount_total) == 0:
                        quotation.with_context(send_email=True).action_confirm()
                        confirmed_orders |= quotation
                    else:
                        _logger.warning(
                            '<%(provider)s> transaction AMOUNT MISMATCH for order %(so_name)s '
                            '(ID %(so_id)s): expected %(so_amount)s, got %(tx_amount)s', {
                                'provider': tx.provider_code,
                                'so_name': quotation.name,
                                'so_id': quotation.id,
                                'so_amount': format_amount(
                                    quotation.env, quotation.amount_total, quotation.currency_id
                                ),
                                'tx_amount': format_amount(tx.env, tx.amount, tx.currency_id),
                            },
                        )
        return confirmed_orders

    def _set_authorized(self, state_message=None, **kwargs):
        """ Override of payment to confirm the quotations automatically. """
        super()._set_authorized(state_message=state_message, **kwargs)
        confirmed_orders = self._check_amount_and_confirm_order()
        confirmed_orders._send_order_confirmation_mail()

    def _log_message_on_linked_documents(self, message):
        """ Override of payment to log a message on the sales orders linked to the transaction.

        Note: self.ensure_one()

        :param str message: The message to be logged
        :return: None
        """
        super()._log_message_on_linked_documents(message)
        self = self.with_user(SUPERUSER_ID)  # Log messages as 'OdooBot'
        for order in self.sale_order_ids or self.source_transaction_id.sale_order_ids:
            order.message_post(body=message)

    def _reconcile_after_done(self):
        """ Override of payment to automatically confirm quotations and generate invoices. """
        confirmed_orders = self._check_amount_and_confirm_order()
        confirmed_orders._send_order_confirmation_mail()

        auto_invoice = str2bool(
            self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice'))
        if auto_invoice:
            # Invoice the sale orders in self instead of in confirmed_orders to create the invoice
            # even if only a partial payment was made.
            self._invoice_sale_orders()
        super()._reconcile_after_done()
        if auto_invoice:
            # Must be called after the super() call to make sure the invoice are correctly posted.
            self._send_invoice()

    def _send_invoice(self):
        template_id = int(self.env['ir.config_parameter'].sudo().get_param(
            'sale.default_invoice_email_template',
            default=0
        ))
        if not template_id:
            return
        template = self.env['mail.template'].browse(template_id).exists()
        if not template:
            return

        for tx in self:
            tx = tx.with_company(tx.company_id).with_context(
                company_id=tx.company_id.id,
            )
            invoice_to_send = tx.invoice_ids.filtered(
                lambda i: not i.is_move_sent and i.state == 'posted' and i._is_ready_to_be_sent()
            )
            invoice_to_send.is_move_sent = True # Mark invoice as sent
            invoice_to_send.with_user(SUPERUSER_ID).message_post_with_source(
                template,
                email_layout_xmlid='mail.mail_notification_layout_with_responsible_signature',
                subtype_xmlid='mail.mt_comment',
            )

    def _cron_send_invoice(self):
        """
            Cron to send invoice that where not ready to be send directly after posting
        """
        if not self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice'):
            return

        # No need to retrieve old transactions
        retry_limit_date = datetime.now() - relativedelta.relativedelta(days=2)
        # Retrieve all transactions matching the criteria for post-processing
        self.search([
            ('state', '=', 'done'),
            ('is_post_processed', '=', True),
            ('invoice_ids', 'in', self.env['account.move']._search([
                ('is_move_sent', '=', False),
                ('state', '=', 'posted'),
            ])),
            ('sale_order_ids.state', 'in', ('sale', 'done')),
            ('last_state_change', '>=', retry_limit_date),
        ])._send_invoice()

    def _invoice_sale_orders(self):
        for tx in self.filtered(lambda tx: tx.sale_order_ids):
            # Create invoices
            tx = tx.with_company(tx.company_id).with_context(company_id=tx.company_id.id)
            confirmed_orders = tx.sale_order_ids.filtered(lambda so: so.state in ('sale', 'done'))
            if confirmed_orders:
                confirmed_orders._force_lines_to_invoice_policy_order()
                invoices = confirmed_orders.with_context(
                    raise_if_nothing_to_invoice=False
                )._create_invoices(final=True)
                # Setup access token in advance to avoid serialization failure between
                # edi postprocessing of invoice and displaying the sale order on the portal
                for invoice in invoices:
                    invoice._portal_ensure_token()
                tx.invoice_ids = [Command.set(invoices.ids)]

    @api.model
    def _compute_reference_prefix(self, provider_code, separator, **values):
        """ Override of payment to compute the reference prefix based on Sales-specific values.

        If the `values` parameter has an entry with 'sale_order_ids' as key and a list of (4, id, O)
        or (6, 0, ids) X2M command as value, the prefix is computed based on the sales order name(s)
        Otherwise, the computation is delegated to the super method.

        :param str provider_code: The code of the provider handling the transaction
        :param str separator: The custom separator used to separate data references
        :param dict values: The transaction values used to compute the reference prefix. It should
                            have the structure {'sale_order_ids': [(X2M command), ...], ...}.
        :return: The computed reference prefix if order ids are found, the one of `super` otherwise
        :rtype: str
        """
        command_list = values.get('sale_order_ids')
        if command_list:
            # Extract sales order id(s) from the X2M commands
            order_ids = self._fields['sale_order_ids'].convert_to_cache(command_list, self)
            orders = self.env['sale.order'].browse(order_ids).exists()
            if len(orders) == len(order_ids):  # All ids are valid
                return separator.join(orders.mapped('name'))
        return super()._compute_reference_prefix(provider_code, separator, **values)

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
