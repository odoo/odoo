from odoo import _, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    def write(self, vals):
        if (
            'account_fiscal_country_id' in vals
            and (jordan_companies := self.filtered(lambda c: c.account_fiscal_country_id.code == 'JO'))
            and self.env['account.move'].search_count([('company_id', 'in', jordan_companies.ids), ('state', '=', 'posted')], limit=1)
        ):
            raise ValidationError(_("You cannot change the fiscal country because you have posted entries."))
        return super().write(vals)
