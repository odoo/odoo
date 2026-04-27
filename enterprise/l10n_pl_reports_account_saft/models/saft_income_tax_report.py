import stdnum

from odoo import fields, models
from odoo.tools import SQL, float_compare, float_repr


class PolishSAFTIncomeTaxCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Polish JPK KR PD Custom Handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        if self.env.company.account_fiscal_country_id.code == 'PL':
            options.setdefault('buttons', []).append({
                'name': self.env._("JPK KR PD"),
                'sequence': 30,
                'action': 'export_file',
                'action_param': 'l10n_pl_export_saft_income_tax_to_xml',
                'file_export_type': self.env._("XML"),
                'always_show': True,
            })

    def _get_missing_fields(self):
        company = self.env.company
        missing_fields = []
        errors = {}
        if not company.vat:
            missing_fields.append(self.env._("VAT Number"))
        if not company.state_id:
            missing_fields.append(self.env._("State"))
        if not company.city:
            missing_fields.append(self.env._("City"))
        if not company.zip:
            missing_fields.append(self.env._("Zip Code"))
        if not company.partner_id._get_street_split()['street_number']:
            missing_fields.append(self.env._("Building Number"))

        if missing_fields:
            errors['missing_company_details_ref'] = {
                'message': self.env._(
                    "The following information is missing from the company configuration:\n- %(missing_fields)s\n"
                    "Please update the company details.",
                    missing_fields="\n- ".join(missing_fields),
                ),
                'action_text': self.env._("Company Details"),
                'action': company._get_records_action(name=self.env._("Company")),
                'level': 'danger',
            }

        if not company.l10n_pl_reports_tax_office_id:
            errors['missing_company_tax_office_ref'] = {
                'message': self.env._("The company’s tax office is missing. Please update it in Settings."),
                'action_text': self.env._("Settings"),
                'action': self.env['res.config.settings']._get_records_action(name="Settings", context={'module': 'account', 'bin_size': False}),
                'level': 'danger',
            }

        return errors

    def _get_saft_tax_totals(self, report, options):
        query = report._get_report_query(options, 'strict_range')
        result = self.env.execute_query(SQL(
            """
            SELECT imd.name AS tag_name,
                   SUM(account_move_line.balance) AS amount
              FROM %(table_references)s
              JOIN account_account aa
                ON account_move_line.account_id = aa.id
              JOIN account_account_account_tag aaat
                ON aa.id = aaat.account_account_id
              JOIN account_account_tag aat
                ON aaat.account_account_tag_id = aat.id
              JOIN ir_model_data imd
                ON imd.model = 'account.account.tag' AND imd.res_id = aat.id AND imd.module = 'l10n_pl'
             WHERE %(search_condition)s
               AND imd.name SIMILAR TO 'K_[1-8]'
          GROUP BY imd.name
            """,
            table_references=query.from_clause,
            search_condition=query.where_clause,
            )
        )
        return {
            **{f"K_{i}": 0.0 for i in range(1, 9)},
            **dict(result),
        }

    def _get_formatted_account_vals_list(self, account_results, initial_balances_map):
        if self.env.company.account_fiscal_country_id.code != 'PL':
            return super()._get_formatted_account_vals_list(account_results, initial_balances_map)

        account_vals_list = []
        for account, results in account_results:
            account_init_bal = initial_balances_map[account.id]
            account_un_earn = results.get('unaffected_earnings', {})
            account_balance = results.get('sum', {})

            initial_debit = account_init_bal.get('debit', 0.0) + account_un_earn.get('debit', 0.0)
            initial_credit = account_init_bal.get('credit', 0.0) + account_un_earn.get('credit', 0.0)

            cum_turnover_debit = initial_debit + account_balance.get('debit', 0.0)
            cum_turnover_credit = initial_credit + account_balance.get('credit', 0.0)

            closing_balance = account_balance.get('balance', 0.0) + account_init_bal.get('balance', 0.0) + account_un_earn.get('balance', 0.0)

            account_vals_list.append(
                {
                    'account_code': account.code,
                    'account_name': account.name,
                    'parent_account_code': account.code,
                    'initial_debit': initial_debit,
                    'initial_credit': initial_credit,
                    'turnover_debit': account_balance.get('debit', 0.0),
                    'turnover_credit': account_balance.get('credit', 0.0),
                    'cum_turnover_debit': cum_turnover_debit,
                    'cum_turnover_credit': cum_turnover_credit,
                    'closing_debit': closing_balance if float_compare(closing_balance, 0.0, 2) >= 0 else 0.0,
                    'closing_credit': -closing_balance if float_compare(closing_balance, 0.0, 2) == -1 else 0.0,
                    'bs_tag': self._get_account_bs_line(account.code),
                }
            )
        return account_vals_list

    def _get_saft_report_income_tax_general_ledger_values(self, report, options):
        template_values = self._saft_prepare_report_values(report, options)
        account_lines = template_values['account_vals_list']
        partners_map = {
            partner_detail['partner'].id: partner_detail['partner']
            for partner_detail in template_values.get('partner_detail_map', {}).values()
        }

        partners = [
            {
                'name': partner.name,
                'vat': partner.vat,
                'country_code': partner.country_code or "",
            }
            for partner in partners_map.values()
        ]

        moves = []
        total_lines_count = 0
        total_balance = 0.0
        for journal_vals in template_values.get('journal_vals_list', []):
            for move_val in journal_vals.get('move_vals_list', []):
                lines = move_val.get('line_vals_list', [])
                amount_total = 0.0
                for line in lines:
                    line['name'] = line['name'] or "/"
                    line['debit_currency'] = abs(line['amount_currency'])
                    line['credit_currency'] = abs(line['amount_currency'])
                    line['currency'] = line['currency_code']
                    line['is_debit'] = bool(line['debit'])

                    if float_compare(line['amount_currency'], 0.0, precision_digits=2) == 1:
                        amount_total += line['amount_currency']

                partner = partners_map.get(move_val['partner_id'], self.env.company.partner_id)
                move_val.update(
                    {
                        'ref': move_val['name'],
                        'description_of_operation': move_val['name'],
                        'journal_name': journal_vals['name'],
                        'journal_code': journal_vals['code'],
                        'invoice_date': move_val['invoice_date'] or move_val['date'],
                        'create_date': move_val['create_date'].date(),
                        'partner_name': partner.name,
                        'amount_total': amount_total,
                        'lines': lines,
                    }
                )
                moves.append(move_val)
                total_lines_count += len(lines)
                total_balance += amount_total

        totals = {
            'moves_count': len(moves),
            'move_lines_count': total_lines_count,
            'total_balance': total_balance,
            'total_debit': template_values.get('total_debit_in_period', 0.0),
            'total_credit': template_values.get('total_credit_in_period', 0.0),
        }

        tax_totals = self._get_saft_tax_totals(report, options)
        self._format_numeric(account_lines, moves, totals, tax_totals)

        return {
            'partners': partners,
            'account_lines': account_lines,
            'moves': moves,
            'totals': totals,
            'tax_totals': tax_totals,
        }

    def l10n_pl_export_saft_income_tax_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        values = self._get_saft_report_income_tax_general_ledger_values(report, options)
        fiscalyear_dates = self.env.company.compute_fiscalyear_dates(fields.Date.to_date(options['date']['date_to']))

        company = self.env.company
        company_values = {
            'currency_name': company.currency_id.name,
            'tax_office': company.l10n_pl_reports_tax_office_id.code,
            'display_name': company.display_name,
            'country_code': company.country_id.code,
            'state_name': company.state_id.name,
            'city': company.city,
            'building_nr': company.partner_id._get_street_split()['street_number'],
            'zip': company.zip,
            'nip': stdnum.pl.nip.compact(company.vat),
        }
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {
                'values': {
                    'date_now': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'date_from': options['date']['date_from'],
                    'date_to': options['date']['date_to'],
                    'date_start': fiscalyear_dates['date_from'],
                    'date_end': fiscalyear_dates['date_to'],
                    'company': company_values,
                    **values,
                },
                'template': 'l10n_pl_reports_account_saft.jpk_kr_pd_template',
                'file_type': 'xml',
            },
            self._get_missing_fields(),
        )
        file_data['file_name'] = "JPK_KR_PD.xml"
        return file_data

    def _get_account_bs_line(self, account_code):
        mapping_rules = [
            (('02',), 'BAAI3_W'),
            (('07.02',), 'BAAI3_A'),
            (('01',), 'BAAII1_W'),
            (('07.01',), 'BAAII1_A'),
            (('08',), 'BAAII2_W'),
            (('03.000.6',), 'BAAIV1_W'),
            (('07.030.1',), 'BAAIV1_A'),
            (('03.000.8', '03.000.9'), 'BAAV1_W'),
            (('03',), 'BAAIV3c_IDAF_W'),
            (('60', '62', '30.000.3', '30.000.4', '30.000.7'), 'BABI1'),
            (('20', '30.000.3'), 'BABII3a_D12'),
            (('22.01', '24.090.1', '29', '64.000.1', '65.000.1'), 'BABII3c_W'),
            (('14.000.2',), 'BABIV'),
            (('1',), 'BABIII1c1_SPKR'),
            (('24.010.2', '24.020.1', '24.090.2'), 'BABIII1b4_IKAF_W'),
            (('80.000.1',), 'BPAI'),
            (('81.03',), 'BPAIII_INN'),
            (('81',), 'BPAII_INN'),
            (('82',), 'BPAV'),
            (('86',), 'BPAVI'),
            (('83',), 'BPBI3_K'),
            (('24.010.1',), 'BPBII3e'),
            (('23.000.2',), 'BPBIII3a'),
            (('21',), 'BPBIII3d_D12'),
            (('22', '23', '24', '28', '64.01', '65.01'), 'BPBIII3i'),
            (('84',), 'BPBIV2_K'),
            (('85',), 'BPBIII4'),
        ]

        for prefixes, tag in mapping_rules:
            if account_code.startswith(prefixes):
                return tag

        return 'INNE'

    def _format_numeric(self, *args: list[dict] | dict):
        for arg in args:
            for item in arg:
                if isinstance(arg, list):
                    self._format_numeric(item)
                elif isinstance(arg[item], (dict, list)):
                    self._format_numeric(arg[item])
                elif isinstance(arg[item], float):
                    arg[item] = float_repr(arg[item], 2)
