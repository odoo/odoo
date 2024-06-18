from odoo import models, fields, api
import pytz


class QrCodePayment(models.Model):
    _name = "l10n_id_pos.qr.code.payment"
    _description = "Record of QR Code Payment"

    currency_id = fields.Many2one("res.currency", string="Currency")
    amount = fields.Float(string="Amount")
    pos_payment_id = fields.Many2one("pos.payment", string="POS Payment")
    qr_img = fields.Text(string="QR Image") #  maybe compute and store true, if expired, regenerate new qr_image
    qr_data = fields.Json(string="QR Data")
    pos_payment_method_id = fields.Many2one("pos.payment.method", string="POS Payment Method")

    # this is the l10n_id specific flow
    def isExpired(self):
        self.ensure_one()
        if self.pos_payment_method_id.qr_code_method == "id_qr":
            now = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Jakarta'), fields.Datetime.now())
            latest_qr_date = fields.Datetime.to_datetime(self.qr_data.get('qris_creation_datetime')).replace(tzinfo=pytz.timezone('Asia/Jakarta'))
            return (now - latest_qr_date).total_seconds() > 1500

        # should call super().isExpired() if not l10n_id specific
        return False

    @api.model
    def _get_or_create(self, amount, free_communication, structured_communication, currency, debtor_partner):
        if free_communication:
            qr_id = self.browse(int(free_communication))
            # if amount || isExpired changed, should update qr_code
            if qr_id.amount != amount or qr_id.isExpired():
                qr_id.amount = amount
                qr_id.generate_qr_code(amount, free_communication, structured_communication, currency, debtor_partner)
            return qr_id

        qr_id = self.create({
            'amount': amount,
            'currency_id': currency,
            'pos_payment_method_id': self.env.context.get('pos_payment_method_id'),
        })
        qr_id.generate_qr_code(amount, free_communication, structured_communication, currency, debtor_partner)
        return qr_id

    def generate_qr_code(self, amount, free_communication, structured_communication, currency, debtor_partner):
        self.ensure_one()
        if float(amount) <= 0 or not structured_communication:
            return False

        payment_bank = self.pos_payment_method_id.journal_id.bank_account_id
        debtor_partner = self.env['res.partner'].browse(debtor_partner)
        currency = self.env['res.currency'].browse(currency)
        qr_code_method = self.pos_payment_method_id.qr_code_method
        if qr_code_method == "id_qr":
            data = payment_bank._l10n_id_qris_get_qr_code(amount, structured_communication)
            self.qr_data = {
                'qris_invoice_id': data.get('qris_invoiceid'),
                'qris_amount': int(amount),
                'qris_creation_datetime': data.get('qris_request_date'),
                'qris_content': data.get('qris_content'),
            }
            self.qr_img = payment_bank.with_context(is_online_qr=True, qr_content=data.get('qris_content')).build_qr_code_base64(
                float(amount), free_communication, structured_communication, currency, debtor_partner, qr_code_method, silent_errors=False)
            return self.qr_img

    def l10n_id_get_qris_qr_status(self):
        self.ensure_one()
        if self.pos_payment_method_id.qr_code_method == "id_qr":
            res_partner_bank = self.pos_payment_method_id.journal_id.bank_account_id
            return res_partner_bank._l10n_id_qris_fetch_status(self.qr_data)
