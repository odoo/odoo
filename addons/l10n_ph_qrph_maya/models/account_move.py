# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import psycopg2

from odoo import fields, models
from odoo.exceptions import UserError

from .res_bank import MayaRequestError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ph_qrph_transaction_ids = fields.One2many(
        comodel_name='l10n_ph.qrph.transaction',
        inverse_name='res_id',
        string="QRPH Transactions",
        domain=[('res_model', '=', 'account.move')],
        groups='account.group_account_invoice',
        copy=False,
    )

    def _generate_qr_code(self, silent_errors=False):
        try:
            # A code handed out earlier is still payable on Maya, so a customer who scanned one just as
            # it went stale has really paid: register that rather than have them pay twice.
            if self.env.context.get('is_online_qr') and self._l10n_ph_qrph_settle_if_paid():
                return None
            return super(
                AccountMove,
                self.with_context(
                    l10n_ph_qrph_model='account.move',
                    l10n_ph_qrph_model_id=str(self.id),
                    l10n_ph_qrph_company_id=self.company_id.id,
                ),
            )._generate_qr_code(silent_errors)
        except MayaRequestError as error:
            # The invoice shows its bank account for manual payments anyway: a Maya outage must not
            # keep the customer from getting it, so it is simply shown without a QR code.
            _logger.warning("No QRPH code on invoice %s: %s", self.id, error)
            return None

    def _l10n_ph_qrph_settle_if_paid(self):
        """ Register the payment of the invoice if any code minted for it was paid.

        :return: whether a payment was registered
        :rtype: bool
        """
        # sudo: this runs for a portal customer looking at the invoice, who may neither read the
        # QRPH transactions and the Maya settings of the bank account nor register a payment.
        # Only what Maya reports is paid.
        invoice = self.sudo()
        if not invoice.filtered_domain(self._l10n_ph_qrph_get_awaiting_payment_domain()):
            return False
        try:
            with self.env.cr.savepoint():
                return bool(invoice._l10n_ph_qrph_register_payment())
        except UserError as error:
            # Looking at the invoice must not fail over a payment that cannot be registered: the cron
            # retries it, and the customer is shown a new code in the meantime.
            _logger.warning("QRPH: could not pay invoice %s: %s", self.id, error)
            return False

    def _l10n_ph_qrph_get_awaiting_payment_domain(self):
        """ The invoices that can still be paid with a QRPH code.

        A code is minted for what is left to pay, so an invoice already partly paid is looked at too.
        Only posted invoices are: a payment cannot be registered on the others (draft, cancelled).
        """
        return [
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('l10n_ph_qrph_transaction_ids', '!=', False),
        ]

    def _l10n_ph_qrph_cron_update_payment_status(self):
        """ Register the payment of every invoice whose QRPH code was paid since the last run.

        Maya is asked about each invoice, which is slow, so the progress is committed after every one.
        """
        invoices = self.search(self._l10n_ph_qrph_get_awaiting_payment_domain())
        IrCron = self.env['ir.cron']
        IrCron._commit_progress(remaining=len(invoices))

        for invoice in invoices:
            try:
                invoice._l10n_ph_qrph_register_payment()
                remaining_time = IrCron._commit_progress(processed=1)
            except psycopg2.OperationalError:  # The invoice was updated concurrently
                IrCron._rollback_progress()
                remaining_time = IrCron._commit_progress(processed=0)  # Let the cron be rescheduled
            except Exception:  # noqa: BLE001 - one invoice must not keep the others from being paid
                IrCron._rollback_progress()
                _logger.exception(
                    "QRPH: could not check the payment of invoice %s; retrying on the next run.", invoice.id,
                )
                remaining_time = IrCron._commit_progress(processed=1)

            if not remaining_time:  # The cron job might be killed soon
                return

    def action_l10n_ph_qrph_update_payment_status(self):
        """ Check with Maya whether the QRPH codes of these invoices were paid, without waiting for the cron. """
        payments = self.env['account.payment']
        for invoice in self.filtered_domain(self._l10n_ph_qrph_get_awaiting_payment_domain()):
            payments |= invoice._l10n_ph_qrph_register_payment()

        if not payments:
            return None
        action = {
            'name': self.env._("Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            return {**action, 'view_mode': 'form', 'res_id': payments.id}
        return {**action, 'view_mode': 'list,form', 'domain': [('id', 'in', payments.ids)]}

    def _l10n_ph_qrph_register_payment(self):
        """ Register a payment on the invoice if Maya reports its QRPH transaction as paid.

        The payment lands on the journal of the bank account that was paid, and is for what the
        customer paid, so that the payment wizard settles any difference with the invoice.

        :return: the created <account.payment>, if any
        """
        self.ensure_one()
        transaction = self.l10n_ph_qrph_transaction_ids._get_paid_transaction(self.amount_residual)
        if not transaction:
            return self.env['account.payment']

        wizard_vals = {'amount': transaction.amount, 'currency_id': transaction.currency_id.id}
        if journal := transaction.bank_id.journal_id.filtered(lambda journal: journal.company_id == self.company_id):
            wizard_vals['journal_id'] = journal.id
        payment = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=self.ids,
        ).create(wizard_vals)._create_payments()
        self._message_log(body=self.env._(
            "Paid with QRPH, Maya payment %(payment)s.",
            payment=transaction._get_html_link(title=transaction.maya_payment_id),
        ))
        # A transaction pays an invoice once. The invoice going back to unpaid because its payment
        # was undone must not have the same transaction pay a second time.
        transaction.settled_date = fields.Datetime.now()
        return payment
