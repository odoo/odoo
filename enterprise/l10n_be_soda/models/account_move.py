from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_edi_decoder(self, file_data, new=False):
        if self.journal_id.type == 'general' and self.journal_id._l10n_be_check_soda_format(file_data['attachment']):
            return self._soda_edi_decoder

        return super()._get_edi_decoder(file_data, new=new)

    def _soda_edi_decoder(self, move, file_data, new=False):
        return move.journal_id._l10n_be_parse_soda_file(file_data['attachment'], skip_wizard=True, move=move)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def write(self, vals):
        if not self.env.user.has_group('account.group_account_user') \
           or 'account_id' not in vals:
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
