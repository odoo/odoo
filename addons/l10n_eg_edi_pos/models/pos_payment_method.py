from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
    l10n_eg_edi_pos_payment_code = fields.Selection(
        selection=[
            ('C', "Cash"),
            ('V', "Visa"),
            ('P', "Points"),
            ('CC', "Cash with contractor"),
            ('VC', "Visa with contractor"),
            ('VO', "Vouchers"),
            ('PR', "Promotion"),
            ('GC', "Gift Card"),
            ('O', "Others"),
        ],
        string="ETA Payment Code",
        default='C',
    )
