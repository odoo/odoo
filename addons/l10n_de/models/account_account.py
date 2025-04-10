from odoo import models, _
from odoo.exceptions import UserError


class AccountAccount(models.Model):
    _inherit = ['account.account']

    def write(self, vals):
        if (
            'code' in vals
            and self.env.company.root_id.account_fiscal_country_id.code == 'DE'
            and any(a.code != vals['code'] for a in self)
        ):
            if self.env['account.move.line'].search_count(
                domain=[('account_id', 'in', self.ids), ("company_id", "=", self.env.company.id)],
                limit=1
            ):
                raise UserError(_("You can not change a Garman company code mapping of an account that has some journal items linked to it in accordance with GoBD."))
        return super().write(vals)
