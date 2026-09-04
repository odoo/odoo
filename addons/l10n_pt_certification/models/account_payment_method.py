from odoo import fields, models

L10N_PT_PAYMENT_MECHANISMS = [
            ('TB', 'Bank Transfer or Authorized Direct Debit'),
            ('CC', 'Credit Card'),
            ('CD', 'Debit Card'),
            ('CH', 'Bank Check'),
            ('CI', 'International Letter of Credit'),
            ('CO', 'Gift Card'),
            ('CS', 'Clearing Balances in Current Account'),
            ('DE', 'E-money'),
            ('LC', 'Bill of Exchange'),
            ('MB', 'Multibanco Reference'),
            ('NU', 'Cash'),
            ('OU', 'Other Mechanism'),
            ('PR', 'Exchange of Goods'),
            ('TR', 'Extra-salary Compensation'),
        ]


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    l10n_pt_payment_mechanism = fields.Selection(
        selection=L10N_PT_PAYMENT_MECHANISMS,
        string='Payment Mechanism',
        default='TB',
        help="This payment method's mechanism according to Portuguese requirements.",
    )
