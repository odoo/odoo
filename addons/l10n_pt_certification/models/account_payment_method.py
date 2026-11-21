from odoo import api, fields, models
from odoo.exceptions import ValidationError

L10N_PT_PAYMENT_MECHANISMS = [
    ('TB', 'Bank Transfer or Authorized Direct Debit'),
    ('CC', 'Credit Card'),
    ('CD', 'Debit Card'),
    ('CH', 'Bank Check'),
    ('CI', 'International Letter of Credit'),
    ('CO', 'Gift Cheque or Card'),
    ('CS', 'Clearing Balances in Current Account'),
    ('DE', 'E-money'),
    ('LC', 'Bill of Exchange'),
    ('MB', 'Multibanco Reference'),
    ('NU', 'Cash'),
    ('OU', 'Other Mechanism'),
    ('PR', 'Exchange of Goods'),
    ('TR', 'Extra-salary Compensation'),
]

# The mechanism a payment method starts with, from the type of its journal.
L10N_PT_PAYMENT_MECHANISM_BY_JOURNAL_TYPE = {'cash': 'NU', 'bank': 'TB', 'credit': 'CC'}


class AccountPaymentMethodLine(models.Model):
    _inherit = 'account.payment.method.line'

    l10n_pt_payment_mechanism = fields.Selection(
        selection=L10N_PT_PAYMENT_MECHANISMS,
        string='Payment Mechanism',
        compute='_compute_l10n_pt_payment_mechanism', store=True, readonly=False, precompute=True,
        help="This payment method's mechanism according to Portuguese requirements.",
    )

    @api.depends('journal_id.type')
    def _compute_l10n_pt_payment_mechanism(self):
        for line in self:
            line.l10n_pt_payment_mechanism = (
                line.l10n_pt_payment_mechanism or L10N_PT_PAYMENT_MECHANISM_BY_JOURNAL_TYPE.get(line.journal_id.type)
            )

    @api.constrains('l10n_pt_payment_mechanism', 'payment_method_id', 'journal_id')
    def _check_l10n_pt_payment_mechanism(self):
        """The SAF-T (PT) exports the mechanism of every receipt (PaymentMechanism): a PT inbound method needs one."""
        if lines := self.filtered(lambda line: (
            line.journal_id.country_code == 'PT' and line.payment_type == 'inbound' and not line.l10n_pt_payment_mechanism
        )):
            raise ValidationError(self.env._(
                "Set a payment mechanism on these payment methods: %(methods)s.",
                methods=", ".join(lines.mapped('name')),
            ))
