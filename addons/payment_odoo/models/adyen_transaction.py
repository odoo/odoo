# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class AdyenTransaction(models.Model):
    _inherit = 'adyen.transaction'

    payment_transaction_id = fields.Many2one(comodel_name='payment.transaction')

    # payment.transaction fields
    invoice_ids = fields.Many2many(related='payment_transaction_id.invoice_ids')
    invoices_count = fields.Integer(related='payment_transaction_id.invoices_count')

    partner_id = fields.Many2one(related='payment_transaction_id.partner_id')
    partner_name = fields.Char(related='payment_transaction_id.partner_name')
    partner_lang = fields.Selection(related='payment_transaction_id.partner_lang')
    partner_email = fields.Char(related='payment_transaction_id.partner_email')
    partner_address = fields.Char(related='payment_transaction_id.partner_address')
    partner_zip = fields.Char(related='payment_transaction_id.partner_zip')
    partner_city = fields.Char(related='payment_transaction_id.partner_city')
    partner_state_id = fields.Many2one(related='payment_transaction_id.partner_state_id')
    partner_country_id = fields.Many2one(related='payment_transaction_id.partner_country_id')
    partner_phone = fields.Char(related='payment_transaction_id.partner_phone')

    @api.model
    def _handle_payment_notification(self, notification_data, payment_tx):
        tx_sudo = self._handle_notification(notification_data)

        if not tx_sudo.payment_transaction_id:
            tx_sudo.payment_transaction_id = payment_tx.id

        # Update fees on payment.transaction
        if float_is_zero(payment_tx.fees, precision_digits=payment_tx.currency_id.decimal_places) and not float_is_zero(tx_sudo.fees, precision_digits=tx_sudo.fees_currency_id.decimal_places):
            amount = tx_sudo.fees_currency_id._convert(tx_sudo.fees, payment_tx.currency_id, self.env.company, tx_sudo.date or fields.Date.today())
            payment_tx.fees = amount

    def _create_missing_tx(self, account_id, transaction, **kwargs):
        tx = super()._create_missing_tx(account_id, transaction, **kwargs)
        if tx.description and not tx.payment_transaction_id:
            payment_tx = self.env['payment.transaction'].search([('reference', '=', tx.description), ('provider', '=', 'odoo')])
            if payment_tx:
                tx.payment_transaction_id = payment_tx.id

                if not transaction.get('disputePspReference') and tx.merchant_amount > 0:
                    tx.total_amount = payment_tx.amount
                    tx.currency_id = payment_tx.currency_id

                    fees_amount = tx.total_amount - tx.merchant_amount
                    tx.fees = payment_tx.currency_id._convert(fees_amount, tx.fees_currency_id, self.env.company, tx.date or fields.Date.today())
                    tx.variable_fees = tx.fees
        return tx

    def action_view_invoices(self):
        self.ensure_one()
        return self.payment_transaction_id.action_view_invoices()
