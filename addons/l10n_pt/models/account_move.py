from odoo import models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_reverse(self):
        for move in self.filtered(lambda m: m.company_id.account_fiscal_country_id.code == "PT"):
            if move.payment_state == 'reversed':
                raise UserError(_("You cannot reverse an invoice that has already been fully reversed."))
        return super().action_reverse()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _l10n_pt_check_validity(self, vals):
        if self.env.company.account_fiscal_country_id.code != 'PT':
            return
        if 'discount' in vals and \
           (vals['discount'] < 0 or vals['discount'] > 100):
            raise UserError(_("Discounts must be between 0% and 100%."))
        if 'debit' in vals and vals['debit'] < 0:
            raise UserError(_("You cannot have a negative debit amount."))
        if 'credit' in vals and vals['credit'] < 0:
            raise UserError(_("You cannot have a negative credit amount."))

    def write(self, vals):
        self._l10n_pt_check_validity(vals)
        return super().write(vals)

    def create(self, vals_list):
        for line in vals_list:
            self._l10n_pt_check_validity(line)
        return super().create(vals_list)
