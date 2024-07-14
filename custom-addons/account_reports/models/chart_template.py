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
            ('type', '=', 'general'),
            ('show_on_dashboard', '=', True)
        ], limit=1)
        if not default_misc_journal:
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
        company._get_and_update_tax_closing_moves(fields.Date.today(), include_domestic=True)
