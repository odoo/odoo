from odoo import _, Command, models
from odoo.exceptions import ValidationError


class CorporateTaxReportHandler(models.AbstractModel):
    _name = 'l10n_ae.corporate.tax.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = "Custom Handler for Corporate TAX Reports in UAE"

    def _custom_options_initializer(self, report, options, previous_options=None):
        # Overrides account.report
        options['buttons'].append({'name': _("Create Entry"), 'action': 'action_create_accounting_entry', 'sequence': 110, 'always_show': True})

    def _custom_line_postprocessor(self, report, options, lines, warnings=None):
        # Overrides account.report
        if warnings is None:
            warnings = {}

        company = self.env['res.company'].browse(report.get_report_company_ids(options)[0])
        if not (company.l10n_ae_tax_report_counterpart_account and company.l10n_ae_tax_report_liabilities_account):
            warnings['l10n_ae_corporate_tax_report.corporate_report_accounts_not_configured'] = {}

        return lines

    def _get_report_payable_amount(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        payable_line = self.env.ref('l10n_ae_corporate_tax_report.ae_corporate_tax_report_line_corporate_tax_amount')
        # Safely take the first key from the column_groups dict because there is only 1 element in the dict
        column_group_key = next(column_group_key for column_group_key in options['column_groups'])

        totals = report._compute_expression_totals_for_each_column_group(report.line_ids.expression_ids, options)
        payable_line_expr = payable_line.expression_ids[0]
        balance_col = totals[column_group_key]
        return next(v for k, v in balance_col.items() if k == payable_line_expr)['value']

    def action_create_accounting_entry(self, options, *args, **kwargs):
        report = self.env.ref('l10n_ae_corporate_tax_report.ae_corporate_tax_report')
        company_id = report.get_report_company_ids(options)[0]
        company = self.env['res.company'].browse(company_id)

        if not (company.l10n_ae_tax_report_counterpart_account and company.l10n_ae_tax_report_liabilities_account):
            raise ValidationError(message=_("The liability accounts for corporate taxes have not been set in the settings."))

        options['export_mode'] = 'file'
        options = report.get_options(options)

        amount = self._get_report_payable_amount(options)
        misc_journal = self.env['account.journal'].search([('code', '=', 'MISC')], limit=1)
        if not misc_journal:
            misc_journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)

        # Create the move
        move = self.env['account.move'].create({
            'ref': _("CIT Closing for the period %(date_period)s", date_period=options['date']['string']),
            'journal_id': misc_journal.id,
            'company_id': company_id,
            'line_ids': [
                Command.create({
                    'account_id': company.l10n_ae_tax_report_counterpart_account.id,
                    'debit': amount,
                }),
                Command.create({
                    'account_id': company.l10n_ae_tax_report_liabilities_account.id,
                    'credit': amount,
                })
            ],
        })

        # Make the action for the created move and return it.
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action |= {
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'res_id': move.id,
        }
        return action

    def l10n_ae_corporate_tax_report_open_settings(self, options):
        return self.env['ir.actions.act_window']._for_xml_id('account.action_account_config')
