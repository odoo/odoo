from odoo import fields, models


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    l10n_ae_billing_frequency = fields.Selection(
        string='Billing Frequency',
        selection=[
            ('DLY', 'Daily'),
            ('WKY', 'Weekly'),
            ('Q15', 'Once in 15 days'),
            ('MTH', 'Monthly'),
            ('Q45', 'Once in 45 days'),
            ('Q60', 'Once in 60 days'),
            ('QTR', 'Quarterly'),
            ('YRL', 'Yearly'),
            ('HYR', 'Half-Yearly'),
            ('OTH', 'Others'),
        ],
    )
