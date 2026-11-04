# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class QRISTransaction(models.Model):
    """QRIS Transaction

    General table to store a certian unique transaction with QRIS details attached
    """
    _name = "l10n_id.qris.transaction"
    _description = "Record of QRIS transactions"

    model = fields.Char(string="Model")  # payment in respond to which model
    model_id = fields.Char(string="Model ID")  # id/uuid

    # Fields that store the QRIS details coming from API request
    qris_invoice_id = fields.Char(readonly=True)
    qris_amount = fields.Integer(readonly=True)
    qris_content = fields.Char(readonly=True)
    qris_creation_datetime = fields.Datetime(readonly=True)

    bank_id = fields.Many2one("res.partner.bank", help="Bank used to generate the current QRIS transaction")
    paid = fields.Boolean(help="Payment Status of QRIS")

    def _get_supported_models(self):
        return ['account.move']

    @api.constrains('model')
    def _constraint_model(self):
        # only allow supported models
        if self.model not in self._get_supported_models():
            raise ValidationError(_("QRIS capability is not extended to model %s yet!", self.model))

    def _get_record(self):
        """ Get the backend invoice record that the qris transaction is handling
        To be overriden in other modules"""
        self.ensure_one()
        if self.model != 'account.move':
            return
        return self.env['account.move'].browse(int(self.model_id)).exists()

    @api.model
    def _get_latest_transaction(self, model, model_id):
        """ Find latest transaction associated to the model and model_id """
        return self.search([('model', '=', model), ('model_id', '=', model_id)], order='qris_creation_datetime desc', limit=1)

    def _l10n_id_get_qris_qr_statuses(self):
        """ Fetch the result of the transaction

        :param invoice_bank_id (Model <res.partner.bank>): bank (with QRIS configuration)
        :returns tuple(bool, dict): paid/unpaid status and status_response from QRIS
        """
        # storing all failure transactions in case final result is unpaid
        unpaid_status_data = []

        # Looping to make requests is far from ideal, but we have no choices as they don't allow getting multiple QR result at once.
        # Ensure to loop in reverse and check from the most recent QR code.
        for transaction in self.sorted(lambda t: t.qris_creation_datetime):
            status_response = self.sudo().bank_id._l10n_id_qris_fetch_status(transaction)
            if status_response['data'].get('qris_status') == 'paid':
                transaction.paid = True
                return {
                    'paid': True,
                    'qr_statuses': [status_response['data']]
                }
            else:
                unpaid_status_data.append(status_response['data'])

        return {
            'paid': False,
            'qr_statuses': unpaid_status_data
        }

    @api.autovacuum
    def _gc_remove_pointless_qris_transactions(self):
        """ Removes unpaid transactions that have been for more than 35 minutes.
        These can no longer be paid and status will no longer change
        """
        time_limit = fields.Datetime.now() - timedelta(seconds=2100)
        transactions = self.env['l10n_id.qris.transaction'].search([('qris_creation_datetime', '<=', time_limit), ('paid', '=', False)])
        transactions.unlink()
