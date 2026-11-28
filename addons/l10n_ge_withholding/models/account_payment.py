from odoo import api, models
from odoo.exceptions import ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    @api.depends('withholding_line_ids.tax_id.l10n_ge_is_gross')
    def _compute_withholding_net_amount(self):
        super()._compute_withholding_net_amount()
        # The company bears the gross withholding: the vendor receives it on top of the net.
        for payment in self:
            payment.withholding_net_amount += sum(payment.withholding_line_ids.filtered('tax_id.l10n_ge_is_gross').mapped('amount'))

    @api.constrains('withhold', 'withholding_line_ids')
    def _check_l10n_ge_gross_withholding_mode(self):
        for payment in self:
            if payment.withhold == 'withhold' and any(payment.withholding_line_ids.tax_id.mapped('l10n_ge_is_gross')):
                raise ValidationError(self.env._("For lines with a gross withholding tax, only 'Withhold and Pay' is allowed."))
