from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    l10n_cz_variable_symbol = fields.Char(
        string="Variable Sysmbol",
        copy=False,
    )

    @staticmethod
    def _find_variable_code(data):
        if isinstance(data, dict):
            if 'variable_code' in data:
                return data['variable_code']
            for value in data.values():
                if variable_code := AccountBankStatementLine._find_variable_code(value):
                    return variable_code

        elif isinstance(data, list):
            for item in data:
                if variable_code := AccountBankStatementLine._find_variable_code(item):
                    return variable_code

        return False

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.company.country_code == 'CZ':
            for vals in vals_list:
                variable_code = vals.get('l10n_cz_variable_symbol')
                if not variable_code and vals.get('transaction_details'):
                    variable_code = self._find_variable_code(vals['transaction_details'])

                if variable_code:
                    vals['l10n_cz_variable_symbol'] = variable_code
                    existing_ref = vals.get('payment_ref') or ''
                    if existing_ref.startswith(variable_code):
                        continue

                    vals['payment_ref'] = f"{variable_code} - {existing_ref}"

        return super().create(vals_list)
