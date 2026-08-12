from odoo import api, models, fields


class PosPayment(models.Model):
    _inherit = "pos.payment"

    viva_com_session_id = fields.Char(help="Session ID of the transaction, stored so that it can be used to refund the payment.")

    @api.model
    def _get_additional_payment_fields(self):
        return super()._get_additional_payment_fields() + ["viva_com_session_id"]

    def _viva_com_verify_transactions(self, transaction_id):
        """
        Confirm with Viva.com that a transaction is genuine and matches this payment line.
        Returns one entry per transaction Viva.com reports for transaction_id:
            {'status': 'not final'}                                still processing
            {'status': 'valid'}                                    finalized and matches the order
            {'status': 'mismatch', 'amount': .., 'currency': ..}   finalized but charged differently
        For 'not final' and 'valid' the amount/currency are omitted; on 'mismatch' they hold the
        amount and (numeric) currency actually captured, so the caller can show them to the customer.
        """
        self.ensure_one()
        if not transaction_id:
            return []
        transactions = self.payment_method_id.sudo()._viva_com_get_transactions(transaction_id)
        results = []
        for transaction in transactions:
            if transaction.get('StatusId') != 'F':
                results.append({'status': 'not final'})
                continue

            session_id = (transaction.get('MerchantTrns') or '').split('/')[0]
            session_matches = (not self.viva_com_session_id
                               or session_id == self.viva_com_session_id
                               or self.amount < 0 and not session_id)
            # A tip added on the terminal can make the captured amount larger.
            amount_matches = self.currency_id.compare_amounts(transaction.get('Amount') or 0.0, self.amount) >= 0
            currency_matches = str(self.currency_id.iso_numeric) == str(transaction.get('CurrencyCode'))
            if not session_matches:
                results.append({
                    'status': 'mismatch',
                    'currency': None,
                    'amount': None,
                })
                continue
            if not currency_matches:
                results.append({
                    'status': 'mismatch',
                    'currency': transaction.get('CurrencyCode'),
                    'amount': None,
                })
                continue
            if not amount_matches:
                results.append({
                    'status': 'mismatch',
                    'currency': None,
                    'amount': transaction.get('Amount'),
                })
                continue
            results.append({'status': 'valid'})

        return results
