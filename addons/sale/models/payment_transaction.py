# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil import relativedelta

from odoo import _, api, Command, fields, models, SUPERUSER_ID
from odoo.tools import str2bool


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'

    sale_order_ids = fields.Many2many('sale.order', 'sale_order_transaction_rel', 'transaction_id', 'sale_order_id',
                                      string='Sales Orders', copy=False, readonly=True)
    sale_order_ids_nbr = fields.Integer(compute='_compute_sale_order_ids_nbr', string='# of Sales Orders')

    def _compute_sale_order_reference(self, order):
        self.ensure_one()
        if self.provider_id.so_reference_type == 'so_name':
            order_reference = order.name
        elif self.provider_id.so_reference_type == 'partner':
            identification_number = order.partner_id.id
            order_reference = '%s/%s' % ('CUST', str(identification_number % 97).rjust(2, '0'))
        else:
            # self.provider_id.so_reference_type is empty
            order_reference = False

        invoice_journal = self.env['account.journal'].search([('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1)
        if invoice_journal:
            order_reference = invoice_journal._process_reference_for_sale_order(order_reference)

        return order_reference

    @api.depends('sale_order_ids')
    def _compute_sale_order_ids_nbr(self):
        for trans in self:
            trans.sale_order_ids_nbr = len(trans.sale_order_ids)

    def _post_process(self):
        """ Override of `payment` to add Sales-specific logic to the post-processing.

        In particular, for pending transactions, we send the quotation by email; for authorized
        transactions, we confirm the quotation; for confirmed transactions, we automatically confirm
        the quotation and generate invoices.
        """
        for pending_tx in self.filtered(lambda tx: tx.state == 'pending'):
            super(PaymentTransaction, pending_tx)._post_process()
            sales_orders = pending_tx.sale_order_ids.filtered(
                lambda so: so.state in ['draft', 'sent']
            )
            sales_orders.filtered(
                lambda so: so.state == 'draft'
            ).with_context(tracking_disable=True).action_quotation_sent()

            if pending_tx.provider_id.code == 'custom':
                for order in pending_tx.sale_order_ids:
                    order.reference = pending_tx._compute_sale_order_reference(order)

            if pending_tx.operation == 'validation':
                continue
            # Send the payment status email.
            # The transactions are manually cached while in a sudoed environment to prevent an
            # AccessError: In some circumstances, sending the mail would generate the report assets
            # during the rendering of the mail body, causing a cursor commit, a flush, and forcing
            # the re-computation of the pending computed fields of the `mail.compose.message`,
            # including part of the template. Since that template reads the order's transactions and
            # the re-computation of the field is not done with the same environment, reading fields
            # that were not already available in the cache could trigger an AccessError (e.g., if
            # the payment was initiated by a public user).
            sales_orders.mapped('transaction_ids')
            sales_orders._send_payment_succeeded_for_order_mail()

        for authorized_tx in self.filtered(lambda tx: tx.state == 'authorized'):
            super(PaymentTransaction, authorized_tx)._post_process()
            confirmed_orders = authorized_tx._check_amount_and_confirm_order()
            if authorized_tx.operation == 'validation':
                continue
            if remaining_orders := (authorized_tx.sale_order_ids - confirmed_orders):
                remaining_orders._send_payment_succeeded_for_order_mail()

        super(PaymentTransaction, self.filtered(
            lambda tx: tx.state not in ['pending', 'authorized', 'done'])
        )._post_process()

        for done_tx in self.filtered(lambda tx: tx.state == 'done'):
            if done_tx.operation != 'validation':
                confirmed_orders = done_tx._check_amount_and_confirm_order()
                (done_tx.sale_order_ids - confirmed_orders)._send_payment_succeeded_for_order_mail()

            auto_invoice = str2bool(
                self.env['ir.config_parameter'].sudo().get_param('sale.automatic_invoice')
            )
            if auto_invoice:
                # Invoice the sales orders of confirmed transactions instead of only confirmed
                # orders to create the invoice even if only a partial payment was made.
                done_tx._invoice_sale_orders()
            super(PaymentTransaction, done_tx)._post_process()  # Post the invoices.
            if auto_invoice and not self.env.context.get('skip_sale_auto_invoice_send'):
                if (
                    str2bool(self.env['ir.config_parameter'].sudo().get_param('sale.async_emails'))
                    and (send_invoice_cron := self.env.ref('sale.send_invoice_cron', raise_if_not_found=False))
                ):
                    send_invoice_cron._trigger()
                else:
                    self._send_invoice()

    def _check_amount_and_confirm_order(self):
        """ Confirm the sales order based on the amount of a transaction.

        Confirm the sales orders only if the transaction amount (or the sum of the partial
        transaction amounts) is equal to or greater than the required amount for order confirmation

        Grouped payments (paying multiple sales orders in one transaction) are not supported.

        :return: The confirmed sales orders.
        :rtype: a `sale.order` recordset
        """
        confirmed_orders = self.env['sale.order']
        for tx in self:
            # We only support the flow where exactly one quotation is linked to a transaction.
            if len(tx.sale_order_ids) == 1:
                quotation = tx.sale_order_ids.filtered(lambda so: so.state in ('draft', 'sent'))
                if quotation and quotation._is_confirmation_amount_reached():
                    quotation.with_context(send_email=True).action_confirm()
                    confirmed_orders |= quotation
        return confirmed_orders

    def _log_message_on_linked_documents(self, message):
        """ Override of payment to log a message on the sales orders linked to the transaction.

        Note: self.ensure_one()

        :param str message: The message to be logged
        :return: None
        """
        super()._log_message_on_linked_documents(message)
        if self.env.uid == SUPERUSER_ID or self.env.context.get('payment_backend_action'):
            author = self.env.user.partner_id
        else:
            author = self.partner_id
        for order in self.sale_order_ids or self.source_transaction_id.sale_order_ids:
            order.message_post(body=message, author_id=author.id)

    def _send_invoice(self):
        # Send messages as OdooBot so that
        #   * logged in users receive the invoice
        #   * the mail and notifications are not sent by the public user
        for tx in self.with_user(SUPERUSER_ID):
            tx = tx.with_company(tx.company_id).with_context(
                company_id=tx.company_id.id,
            )
            invoice_to_send = tx.invoice_ids.filtered(
                lambda i: not i.is_move_sent and i.state == 'posted' and i._is_ready_to_be_sent()
            )
            invoice_to_send.is_move_sent = True # Mark invoice as sent

            send_context = {'allow_raising': False, 'allow_fallback_pdf': True}
            default_template_param = (
                self.env['ir.config_parameter']
                .sudo()
                .get_param('sale.default_invoice_email_template', False)
            )
            if default_template_param:
                mail_template = self.env['mail.template'].sudo().browse(int(default_template_param))
                if mail_template.exists():
                    send_context['mail_template'] = mail_template

            tx.env['account.move.send']._generate_and_send_invoices(
                invoice_to_send,
                **send_context,
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
            ('sale_order_ids.state', '=', 'sale'),
            ('last_state_change', '>=', retry_limit_date),
        ])._send_invoice()

    def _invoice_sale_orders(self):
        for tx in self.filtered(lambda tx: tx.sale_order_ids):
            tx = tx.with_company(tx.company_id)

            confirmed_orders = tx.sale_order_ids.filtered(lambda so: so.state == 'sale')
            if confirmed_orders:
                # Filter orders between those fully paid and those partially paid.
                fully_paid_orders = confirmed_orders.filtered(lambda so: so._is_paid())

                # Create a down payment invoice for partially paid orders
                downpayment_invoices = (
                    confirmed_orders - fully_paid_orders
                )._generate_downpayment_invoices()

                # For fully paid orders create a final invoice.
                fully_paid_orders._force_lines_to_invoice_policy_order()
                final_invoices = fully_paid_orders.with_context(
                    raise_if_nothing_to_invoice=False
                )._create_invoices(final=True)
                invoices = downpayment_invoices + final_invoices

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
            action['view_mode'] = 'list,form'
            action['domain'] = [('id', 'in', sale_order_ids)]
        return action
