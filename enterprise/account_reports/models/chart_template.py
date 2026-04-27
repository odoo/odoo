# coding: utf-8
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)

        company = company or self.env.company
        default_misc_journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(company),
                ('type', '=', 'general')
            ], limit=1)
        if not default_misc_journal:
            raise ValidationError(_("No default miscellaneous journal could be found for the active company"))

        company.update({
            'totals_below_sections': company.anglo_saxon_accounting,
            'account_tax_periodicity_journal_id': default_misc_journal,
            'account_tax_periodicity_reminder_day': 7,
        })
        default_misc_journal.show_on_dashboard = True

        generic_tax_report = self.env.ref('account.generic_tax_report')
        tax_report = self.env['account.report'].search([
            ('availability_condition', '=', 'country'),
            ('country_id', '=', company.country_id.id),
            ('root_report_id', '=', generic_tax_report.id),
        ], limit=1)
        if not tax_report:
            tax_report = generic_tax_report

        _dummy, period_end = company._get_tax_closing_period_boundaries(fields.Date.today(), tax_report)
        activity = company._get_tax_closing_reminder_activity(tax_report.id, period_end)
        if not activity:
            company._generate_tax_closing_reminder_activity(tax_report, period_end)
