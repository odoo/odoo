# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import fields, models

from .res_bank import MayaRequestError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_ph_qrph_transaction_ids = fields.One2many(
        comodel_name='l10n_ph.qrph.transaction',
        inverse_name='res_id',
        string="QRPH Codes",
        domain=[('res_model', '=', 'account.move')],
        groups='account.group_account_invoice',
        copy=False,
    )

    def _generate_qr_code(self, silent_errors=False):
        try:
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

    def _l10n_ph_qrph_cron_update_payment_status(self):
        """ Register the payment of every invoice whose QRPH code was paid since the last run.

        A code is minted for what is left to pay, so an invoice already partly paid is looked at too.
        """
        invoices = self.search([
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('l10n_ph_qrph_transaction_ids', '!=', False),
        ])
        return invoices._l10n_ph_qrph_update_payment_status()

    def action_l10n_ph_qrph_update_payment_status(self):
        """ Check with Maya whether the QRPH codes of these invoices were paid, without waiting for the cron. """
        invoices = self.filtered_domain([
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('l10n_ph_qrph_transaction_ids', '!=', False),
        ])
        return invoices._l10n_ph_qrph_update_payment_status()

    def _l10n_ph_qrph_update_payment_status(self):
        """ Register a payment on the invoices of self whose QRPH code Maya reports as paid. """
        paid_invoices = self.env['account.move']
        settled_transactions = self.env['l10n_ph.qrph.transaction']
        bodies = {}
        for invoice in self:
            if transaction := invoice.l10n_ph_qrph_transaction_ids._get_paid_transaction():
                paid_invoices |= invoice
                settled_transactions |= transaction
                bodies[invoice.id] = self.env._(
                    "Paid with QRPH, Maya payment %(payment)s.",
                    payment=transaction._get_html_link(title=transaction.maya_payment_id),
                )

        if not paid_invoices:
            return None

        paid_invoices._message_log_batch(bodies=bodies)
        payments = self.env['account.payment.register'].with_context(
            active_model='account.move',
            active_ids=paid_invoices.ids,
        ).create({'group_payment': False}).action_create_payments()
        # A code pays an invoice once. The invoice going back to unpaid because its payment was
        # undone must not have the same code pay a second time.
        settled_transactions.settled_date = fields.Datetime.now()
        return payments
