from odoo import api, fields, models
from odoo.tools import float_is_zero
from odoo.addons.l10n_kh_aba_payway import const


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    allow_qr_on_bill = fields.Boolean(
        string="Allow QR on Bill",
        help="If checked, a QR code for this payment method will be generated and printed on the customer bill.",
        default=False,
    )

    digital_qr_lifetime = fields.Integer(
        string="QR on screen expire time (minute)",
        related='journal_id.bank_account_id.digital_qr_lifetime',
        readonly=True,
    )

    bill_qr_lifetime = fields.Integer(
        string="QR on Bill expire time (Minute)",
        related='journal_id.bank_account_id.bill_qr_lifetime',
        readonly=True,
    )

    def get_qr_code(self, amount, free_communication, structured_communication, currency, debtor_partner):
        self.ensure_one()

        if self.qr_code_method in const.PAYMENT_METHODS_CODES and float_is_zero(amount, precision_rounding=currency.rounding):
            # Odoo attempt to call default qr generation with amount is False
            # which can be use when POS is offline
            # to prevent it return False when pos is offline
            return False

        if self.payment_method_type == 'qr_code' or self.qr_code_method in const.PAYMENT_METHODS_CODES:

            qr_type = self._context.get('qr_type')
            if qr_type == "bill" and (self.qr_code_method == const.PAYMENT_METHODS_MAPPING['abapay_khqr'] and not self.allow_qr_on_bill):
                return False

        return super().get_qr_code(
            amount,
            free_communication,
            structured_communication,
            currency,
            debtor_partner,
        )

    def payway_cancel_transaction(self, qr_tran_id):
        """Call res.partner.bank close payway transaction method"""

        self.ensure_one()
        if self.payment_method_type != 'qr_code' or not self.qr_code_method in const.PAYMENT_METHODS_CODES:
            return True

        payment_bank = self.journal_id.bank_account_id
        payment_bank._payway_api_close_transaction(qr_tran_id)

    def payway_verify_transaction(self, qr_tran_id):

        self.ensure_one()
        if self.payment_method_type != 'qr_code' or not self.qr_code_method in const.PAYMENT_METHODS_CODES:
            return True

        payment_bank = self.journal_id.bank_account_id
        response = payment_bank._payway_api_check_transaction(qr_tran_id)

        is_payment_complete = str(response['data']['payment_status_code']) == '0'
        return is_payment_complete

    @api.model
    def _load_pos_data_fields(self, config_id):
        res = super()._load_pos_data_fields(config_id)

        fields = ['qr_code_method', 'digital_qr_lifetime', 'bill_qr_lifetime', 'allow_qr_on_bill']
        for field in fields:
            if field not in res:
                res.append(field)

        return res
