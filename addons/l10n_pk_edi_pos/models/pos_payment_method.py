from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_pk_edi_pos_fbr_payment_code = fields.Selection(
        selection=[
            ('1', "Cash"),
            ('2', "Card"),
            ('6', "Cheque"),
        ],
        string="FBR Payment Code",
        help="Payment code reported to the FBR for this payment method.",
    )
