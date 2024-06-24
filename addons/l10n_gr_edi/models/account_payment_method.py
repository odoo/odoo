from odoo import fields, models, api


PAYMENT_METHOD_MAP = {
    '1': '1 - Domestic Payments Account Number',
    '2': '2 - Foreign Payments Account Number',
    '3': '3 - Cash',
    '4': '4 - Check',
    '5': '5 - On credit',
    '6': '6 - Web Banking',
    '7': '7 - POS / e-POS',
}
PAYMENT_METHOD_SELECTION = list(PAYMENT_METHOD_MAP.items())


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    l10n_gr_edi_payment_method_id = fields.Selection(
        selection=PAYMENT_METHOD_SELECTION,
        string='MyDATA Payment Method',
        help='Specify the payment method classification required for sending invoice payment data to MyDATA',
    )

    @api.depends('l10n_gr_edi_payment_method_id')
    def _compute_name(self):
        for method in self:
            if method.l10n_gr_edi_payment_method_id:
                method.name = PAYMENT_METHOD_MAP[method.l10n_gr_edi_payment_method_id]
