from odoo import models, _


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code == 'BE':
            options['buttons'].append({
                'name': _('Annual Accounts'),
                'sequence': 40,
                'action': 'export_file',
                'action_param': 'l10n_be_get_annual_accounts',
                'file_export_type': _('TXT'),
            })


    def l10n_be_get_annual_accounts(self, options):
        """ Export the general ledger as a tab-delimited txt file (csv style).
        The information exported are only the accounts code, name, debit and credit.
        There should be no thousand separator, the decimal separator must be a comma, et there should be zeros if no values.
        """
        # Get the report
        report = self.env['account.report'].with_context(no_format=True).browse(options['report_id'])
        print_options = report.get_options(previous_options=options)

        # Get the lines of the report, then filter to only use the account lines (the other aren't needed.)
        lines = report._get_lines(print_options)
        account_lines = []
        account_ids = []
        for line in lines:
            model, account_id = report._parse_line_id(line['id'])[-1][1:]
            if model != 'account.account':
                continue
            account_lines.append(line)
            account_ids.append(account_id)
        accounts = self.env['account.account'].browse(account_ids)

        # As we export for the current period, only the first column group is relevant
        column_group = list(options.get('column_groups', {}).keys())[0]
        columns = options.get('columns', [])
        column_name_to_index = {col['expression_label']: idx for idx, col in enumerate(columns) if col['column_group_key'] == column_group}

        # Build the txt
        res = []
        for line in account_lines:
            account_id = report._parse_line_id(line['id'])[-1][-1]
            account = accounts.filtered(lambda acc: acc.id == account_id)
            # For debit and credit, decimal separator should always be a comma in this export. (Belgian format)
            # As we can't yet babel to format to numbers to the belgium format without separators before babel 2.9,
            # We'll resort to simply cast the amount in a string and replace dots with commas.
            debit = str(line['columns'][column_name_to_index['debit']]['no_format'])
            debit_formatted = debit.replace('.', ',')
            credit = str(line['columns'][column_name_to_index['credit']]['no_format'])
            credit_formatted = credit.replace('.', ',')
            res.append(f'{account.code}\t{account.name}\t{debit_formatted}\t{credit_formatted}')
        return {
            'file_name': 'annual_accounts.txt',
            'file_content': '\n'.join(res).encode(),
            'file_type': 'txt',
        }
