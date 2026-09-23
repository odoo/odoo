# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, Command
from odoo.tools import format_date
from odoo.tools.translate import _

from odoo.addons.payment import utils as payment_utils
from odoo.tools.image import image_data_uri


class AccountMove(models.Model):
    _inherit = 'account.move'

    transaction_ids = fields.Many2many(
        string="Transactions", comodel_name='payment.transaction',
        relation='account_invoice_transaction_rel', column1='invoice_id', column2='transaction_id',
        readonly=True, copy=False)
    authorized_transaction_ids = fields.Many2many(
        string="Authorized Transactions", comodel_name='payment.transaction',
        compute='_compute_authorized_transaction_ids', readonly=True, copy=False,
        compute_sudo=True)
    transaction_count = fields.Integer(
        string="Transaction Count", compute='_compute_transaction_count'
    )
    amount_paid = fields.Monetary(
        string="Amount paid",
        compute='_compute_amount_paid'
    )

    @api.depends('transaction_ids')
    def _compute_authorized_transaction_ids(self):
        for invoice in self:
            invoice.authorized_transaction_ids = invoice.transaction_ids.filtered(
                lambda tx: tx.state == 'authorized'
            )

    @api.depends('transaction_ids')
    def _compute_transaction_count(self):
        for invoice in self:
            invoice.transaction_count = len(invoice.transaction_ids)

    @api.depends('transaction_ids')
    def _compute_amount_paid(self):
        """ Sum all the transaction amount for which state is in 'authorized' or 'done'
        """
        for invoice in self:
            invoice.amount_paid = sum(
                invoice.transaction_ids.filtered(
                    lambda tx: tx.state in ('authorized', 'done')
                ).mapped('amount')
            )

    def _has_to_be_paid(self):
        self.ensure_one()
        transactions = self.transaction_ids.filtered(lambda tx: tx.state in ('pending', 'authorized', 'done'))
        pending_transactions = transactions.filtered(
            lambda tx: tx.state in {'pending', 'authorized'}
                       and tx.provider_code not in {'none', 'custom'})
        enabled_feature = self.env['ir.config_parameter'].sudo().get_bool(
            'account_payment.enable_portal_payment'
        )
        return enabled_feature and bool(
            (self.amount_residual or not transactions)
            and self.state == 'posted'
            and self.payment_state in ('not_paid', 'in_payment', 'partial')
            and not self.currency_id.is_zero(self.amount_residual)
            and self.amount_total
            and self.move_type == 'out_invoice'
            and not pending_transactions
        )

    def _get_online_payment_error(self):
        """
        Returns the appropriate error message to be displayed if _has_to_be_paid() method returns False.
        """
        self.ensure_one()
        transactions = self.transaction_ids.filtered(lambda tx: tx.state in ('pending', 'authorized', 'done'))
        pending_transactions = transactions.filtered(
            lambda tx: tx.state in {'pending', 'authorized'}
                       and tx.provider_code not in {'none', 'custom'})
        enabled_feature = self.env['ir.config_parameter'].sudo().get_bool(
            'account_payment.enable_portal_payment'
        )
        errors = []
        if not enabled_feature:
            errors.append(_("This invoice cannot be paid online."))
        if transactions or self.currency_id.is_zero(self.amount_residual):
            errors.append(_("There is no amount to be paid."))
        if self.state != 'posted':
            errors.append(_("This invoice isn't posted."))
        if self.currency_id.is_zero(self.amount_residual):
            errors.append(_("This invoice has already been paid."))
        if self.move_type != 'out_invoice':
            errors.append(_("This is not an outgoing invoice."))
        if pending_transactions:
            errors.append(_("There are pending transactions for this invoice."))
        return '\n'.join(errors)

    @api.private
    def get_portal_last_transaction(self):
        self.ensure_one()
        return self.with_context(active_test=False).sudo().transaction_ids._get_last()

    def payment_action_capture(self):
        """ Capture all transactions linked to this invoice. """
        self.ensure_one()
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        return self.sudo().transaction_ids.action_capture()

    def payment_action_void(self):
        """ Void all transactions linked to this invoice. """
        payment_utils.check_rights_on_recordset(self)

        # In sudo mode to bypass the checks on the rights on the transactions.
        self.sudo().authorized_transaction_ids.action_void()

    def action_view_payment_transactions(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment.action_payment_transaction')

        if len(self.transaction_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.transaction_ids.id
            action['views'] = []
        else:
            action['domain'] = [('id', 'in', self.transaction_ids.ids)]

        return action

    def _get_default_payment_link_values(self):
        next_payment_values = self._get_invoice_next_payment_values()
        amount_due = next_payment_values.get('amount_due')
        additional_info = {}
        open_installments = []
        installment_state = next_payment_values.get('installment_state')
        next_amount_to_pay = next_payment_values.get('next_amount_to_pay')
        if installment_state in ('next', 'overdue'):
            open_installments = []
            for installment in next_payment_values.get('not_reconciled_installments'):
                data = {
                    'type': installment['type'],
                    'number': installment['number'],
                    'amount': installment['amount_residual_currency_unsigned'],
                    'date_maturity': format_date(self.env, installment['date_maturity']),
                }
                open_installments.append(data)

        elif installment_state == 'epd':
            amount_due = next_amount_to_pay  # with epd, next_amount_to_pay is the invoice amount residual
            additional_info.update({
                'has_eligible_epd': True,
                'discount_date': next_payment_values.get('discount_date')
            })

        return {
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'open_installments': open_installments,
            'amount': next_amount_to_pay,
            'invoice_amount_due': amount_due,
            **additional_info
        }

    def _generate_portal_payment_qr(self):
        self.ensure_one()
        portal_url = self._get_portal_payment_link()
        barcode = self.env['ir.actions.report'].barcode(barcode_type="QR", value=portal_url, width=128, height=128, quiet=False)
        return image_data_uri(barcode)

    def _get_portal_payment_link(self):
        self.ensure_one()
        payment_link_wizard = self.env['payment.link.wizard'].with_context(
            active_id=self.id, active_model=self._name
        ).create({})
        return payment_link_wizard.link

    def _interco_filter_moves(self):
        return self.filtered(lambda m:
                             m.is_invoice()
                             and m.payment_state in ('not_paid', 'partial', 'in_payment')
                             and m.company_id.account_interco_clearing_journal_id
                             and m.transaction_ids.payment_id
                             and m.company_id not in m.transaction_ids.payment_id.company_id
                             and ((
                                 m.is_inbound()
                                 and m.company_id.account_interco_receivable_id
                                 and m.transaction_ids.payment_id.company_id.account_interco_payable_id
                             ) or (
                                 m.is_outbound()
                                 and m.company_id.account_interco_payable_id
                                 and m.transaction_ids.payment_id.company_id.account_interco_receivable_id
                             ))
                             and m.transaction_ids.payment_id.filtered(
                                 lambda x: x.state in ('in_process', 'paid')
                                 and x.company_id != m.company_id
                                 and x.company_id.account_interco_clearing_journal_id.id
                             )
                             )

    def _post(self, soft=True):
        """ Check if there are pending payments on other companies that wait for this move. """
        moves = super()._post(soft)
        if interco_moves := moves.sudo()._interco_filter_moves():
            for invoice in interco_moves:
                transactions = invoice.sudo().transaction_ids.filtered(lambda tx: tx.state in ('authorized', 'done'))
                invoice._check_interco_clearing(transactions.payment_id)
        return moves

    def _check_interco_clearing(self, payments):
        self.ensure_one()

        is_sale = self.is_sale_document()
        label = f"{self.partner_id.display_name} / {self.name}"

        for payment in payments:
            _liquidity_lines, counterpart_lines, _writeoff_lines = payment._seek_for_lines()
            if counterpart_lines:
                counterpart_account = counterpart_lines.account_id
                clearing_balance = -sum(line.balance for line in counterpart_lines)
                clearing_amount_currency = -sum(line.amount_currency for line in counterpart_lines)

                other_interco_account = (
                    payment.company_id.account_interco_payable_id
                    if is_sale
                    else payment.company_id.account_interco_receivable_id
                )
                payment_clearing = self.env['account.move'].with_company(payment.company_id).create({
                    'move_type': 'entry',
                    'journal_id': payment.company_id.account_interco_clearing_journal_id.id,
                    'ref': payment.memo,
                    'line_ids': [
                        Command.create({
                            'name': label,
                            'account_id': counterpart_account.id,
                            'partner_id': self.partner_id.id,
                            'currency_id': payment.currency_id.id,
                            'amount_currency': clearing_amount_currency,
                            'balance': clearing_balance
                        }),
                        Command.create({
                            'name': label,
                            'account_id': other_interco_account.id,
                            'partner_id': self.company_id.partner_id.id,
                            'currency_id': payment.currency_id.id,
                            'amount_currency': -clearing_amount_currency,
                            'balance': -clearing_balance
                        }),
                    ]
                })
                payment_clearing.action_post()
                payment_clearing_line = payment_clearing.line_ids.filtered(lambda line: line.account_id == counterpart_account)
                (counterpart_lines + payment_clearing_line).reconcile()

        payment = payments[0]
        invoice_lines = self.line_ids.filtered(lambda acc: acc.account_type in ('asset_receivable', 'liability_payable'))
        invoice_line_account = invoice_lines[:1].account_id
        total_invoice_balance = sum(invoice_lines.mapped('balance'))
        clearing_counterpart_balance = -total_invoice_balance

        self_interco_account = (
            self.company_id.account_interco_receivable_id
            if is_sale
            else self.company_id.account_interco_payable_id
        )
        memos = ", ".join(payments.mapped("memo"))
        entry = self.env['account.move'].with_company(self.company_id).create({
            'move_type': 'entry',
            'journal_id': self.company_id.account_interco_clearing_journal_id.id,
            'ref': self.env._("Interco Settlement - %s", memos),
            'line_ids': [
                Command.create({
                    'name': label,
                    'account_id': self_interco_account.id,
                    'partner_id': payment.company_id.partner_id.id,
                    'currency_id': self.company_id.currency_id.id,
                    'balance': -clearing_counterpart_balance,
                }),
                Command.create({
                    'name': label,
                    'account_id': invoice_line_account.id,
                    'partner_id': payment.partner_id.id,
                    'currency_id': self.company_id.currency_id.id,
                    'balance': clearing_counterpart_balance,
                }),
            ],
        })
        entry.action_post()

        entry_receivable_line = entry.line_ids.filtered(lambda line: line.account_id == invoice_line_account)
        (entry_receivable_line + invoice_lines).reconcile()
