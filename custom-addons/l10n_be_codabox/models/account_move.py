from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        if 'account_id' not in vals:
            return super().write(vals)
        for line in self.filtered(lambda l: l.company_id.account_fiscal_country_id.code == 'BE'):
            suspense_account = line.company_id.account_journal_suspense_account_id
            if line.account_id == suspense_account:
                if mapping := self.env['soda.account.mapping'].search([
                    ('company_id', '=', line.company_id.id),
                    ('name', '=', line.name),
                    '|',
                        ('account_id', '=', False),
                        ('account_id', '=', suspense_account.id),
                ]):
                    mapping.account_id = vals['account_id']
        return super().write(vals)
