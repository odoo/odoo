from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    l10n_ma_reports_payment_method = fields.Selection(
        [
            ('1', 'Cash'),
            ('2', 'Check'),
            ('3', 'Direct Debit'),
            ('4', 'Bank Transfer'),
            ('5', 'Bill of Exchange'),
            ('6', 'Compensation'),
            ('7', 'Others'),
        ],
        string='Payment Channel',
        default='7',
        help='Payment method for Moroccan EDI. If left empty it will default to "Other" on the EDI declaration.'
    )
