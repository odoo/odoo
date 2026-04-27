# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, Command, models
from odoo.exceptions import UserError


class CorporateTaxReportHandler(models.AbstractModel):
    _name = 'l10n_bd.corporate.tax.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = "Custom Handler for Corporate TAX Reports in Bangladesh"

    def _custom_options_initializer(self, report, options, previous_options):
        # EXTEND account.report
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        options['buttons'].append({'name': _("Closing Entry"), 'action': 'action_create_accounting_entry', 'sequence': 110, 'always_show': True})

    def action_create_accounting_entry(self, options):
        company_ids = self.env['account.report'].get_report_company_ids(options)
        if len(company_ids) != 1:
            raise UserError(_("Please select a single company in order to create the closing entry."))

        company = self.env['res.company'].browse(company_ids[0])
        misc_journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        amount = self._get_report_payable_amount(options)

        if not company.l10n_bd_corporate_tax_liability and not company.l10n_bd_corporate_tax_expense:
            raise UserError(_("Make sure to choose the liabilities and counter part accounts in the accounting settings"))

        # Create the move
        move = self.env['account.move'].create({
            'journal_id': misc_journal.id,
            'company_id': company.id,
            'ref': _("Corporate Tax Closing for the period %(date_period)s", date_period=options['date']['string']),
            'line_ids': [
                Command.create({
                    'account_id': company.l10n_bd_corporate_tax_liability.id,
                    'balance': -amount,
                }),
                Command.create({
                    'account_id': company.l10n_bd_corporate_tax_expense.id,
                    'balance': amount,
                }),
            ],
        })

        # Make the action for the created move and return it.
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action.update({
            'views': [(self.env.ref('account.view_move_form').id, 'form')],
            'res_id': move.id,
        })
        return action

    def _get_report_payable_amount(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        report_lines = report._get_lines(options)
        cop_line = self.env.ref('l10n_bd_reports.bd_corporate_tax_report_cop_tax_amount')

        line_id = report._build_line_id([(None, 'account.report', report.id), (None, 'account.report.line', cop_line.id)])
        payable_line_info = next(report_line for report_line in report_lines if report_line['id'] == line_id)

        return payable_line_info['columns'][0]['no_format']
