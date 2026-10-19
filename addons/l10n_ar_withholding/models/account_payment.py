from odoo import api, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.constrains('state', 'withholding_line_ids')
    def _check_withholding_line_sequence_number(self):
        # AR withholdings are certificates: they must be numbered once the payment is posted.
        for payment in self.filtered(lambda p: p.state in ('paid', 'reconciled') and p.country_code == 'AR'):
            for line in payment.withholding_line_ids:
                if not line.name and not line.withholding_sequence_id:
                    raise ValidationError(self.env._(
                        "Please enter Sequence Number for tax %(tax_name)s",
                        tax_name=line.tax_id.name,
                    ))

    @api.depends('company_id.account_fiscal_country_id')
    def _compute_withholding_hide_name(self):
        # EXTENDS 'l10n_account_withholding_tax' - always display sequence/name for AR
        ar_payments = self.filtered(lambda p: p.country_code == 'AR')
        ar_payments.withholding_hide_name = False
        super(AccountPayment, self - ar_payments)._compute_withholding_hide_name()
