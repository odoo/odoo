# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import csv
import io

from odoo.exceptions import UserError
from odoo.tools import street_split

from odoo import api, models, _


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _customize_warnings(self, report, options, all_column_groups_expression_totals, warnings=None):
        super()._customize_warnings(report, options, all_column_groups_expression_totals, warnings=warnings)
        is_dk_company = self.env.company.account_fiscal_country_id.code == 'DK'
        if not is_dk_company or warnings is None:
            return

        if not any(self.env.company.partner_id.bank_ids):
            company_data_warning = warnings.setdefault('account_saft.company_data_warning', {'alert_type': 'warning', 'args': ''})
            company_data_warning['args'] += f"{', ' if company_data_warning['args'] else ''}{_('the account number')}"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'DK':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_dk_export_saft_to_xml',
                'file_export_type': _('XML')
            })
            options['buttons'].append({
                'name': _('CSV'),
                'sequence': 55,
                'action': 'export_file',
                'action_param': 'l10n_dk_export_general_ledger_csv',
                'file_export_type': _('CSV')
            })

    @api.model
    def l10n_dk_export_saft_to_xml(self, options):
        if not any(self.env.company.partner_id.bank_ids):
            raise UserError(_('An account number is needed to export the SAF-T'))

        report = self.env['account.report'].browse(options['report_id'])
        template_vals = self._l10n_dk_saft_prepare_report_values(report, options)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': template_vals, 'template': 'l10n_dk_reports.saft_template', 'file_type': 'xml'},
            template_vals['errors'],
        )
        return file_data

    @api.model
    def _l10n_dk_saft_prepare_report_values(self, report, options):
        template_vals = self._saft_prepare_report_values(report, options)
        template_vals.update({
            'xmlns': "urn:StandardAuditFile-Taxation-Financial:DK",
            'file_version': '1.0',
            'street_split': street_split,
        })
        for tax in template_vals['tax_vals_list']:
            # The documentation describes the `EffectiveDate` as "Representing the starting date for this entry."
            # The postgres `create_date` is the date from which the record can be used in the system and thus is the
            # more suitable one in this context.
            tax['effective_date'] = tax['create_date'].strftime('%Y-%m-%d')
        return template_vals

    def _saft_get_account_type(self, account_type):
        # OVERRIDE account_saft/models/account_general_ledger
        if self.env.company.account_fiscal_country_id.code != 'DK':
            return super()._saft_get_account_type(account_type)

        # possible type: Asset/Liability/Sale/Expense/Other
        account_type_dict = {
            "asset_receivable": 'Asset',
            "asset_cash": 'Asset',
            "asset_current": 'Asset',
            "asset_non_current": 'Asset',
            "asset_prepayments": 'Asset',
            "asset_fixed": 'Asset',
            "liability_payable": 'Liability',
            "liability_credit_card": 'Liability',
            "liability_current": 'Liability',
            "liability_non_current": 'Liability',
            "equity": 'Liability',
            "equity_unaffected": 'Liability',
            "income": 'Sale',
            "income_other": 'Sale',
            "expense": 'Expense',
            "expense_depreciation": 'Expense',
            "expense_direct_cost": 'Expense',
            "off_balance": 'Other',
        }
        return account_type_dict[account_type]

    @api.model
    def l10n_dk_export_general_ledger_csv(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        # account number, account name, balance
        # _20230131 is not the export date, but rather the date at which the norm of this csv export was enforced
        csv_lines = [("KONTONUMMER_20230131", "KONTONAVN_20230131", "VAERDI_20230131")]
        # fold all report lines to make sure we only get the account details
        new_options = report.get_options(previous_options={**options, 'unfolded_lines': [], 'unfold_all': False})

        balance_index = [c['expression_label'] for c in options['columns']].index('balance')
        for line in filter(lambda line: self.env['account.report']._get_markup(line['id']) != 'total', report._get_lines(new_options)):
            account_number, account_name = line['name'].split(maxsplit=1)
            account_balance = int(line['columns'][balance_index]['no_format'])  # balance value must be a whole number
            csv_lines.append((account_number, account_name, account_balance))

        with io.StringIO() as buf:
            writer = csv.writer(buf, delimiter=',')
            writer.writerows(csv_lines)
            content = buf.getvalue().encode()

        return {
            'file_name': report.get_default_report_filename(options, 'csv'),
            'file_content': content,
            'file_type': 'csv',
        }
