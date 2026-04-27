# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from calendar import monthrange

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import format_date
from odoo.tools import date_utils


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    totals_below_sections = fields.Boolean(related='company_id.totals_below_sections', string='Add totals below sections', readonly=False,
                                           help='When ticked, totals and subtotals appear below the sections of the report.')
    account_tax_periodicity = fields.Selection(related='company_id.account_tax_periodicity', string='Periodicity', readonly=False, required=True)
    account_tax_periodicity_reminder_day = fields.Integer(related='company_id.account_tax_periodicity_reminder_day', string='Reminder', readonly=False, required=True)
    account_tax_periodicity_journal_id = fields.Many2one(related='company_id.account_tax_periodicity_journal_id', string='Journal', readonly=False)

    account_reports_show_per_company_setting = fields.Boolean(compute="_compute_account_reports_show_per_company_setting")

    def open_tax_group_list(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Tax groups',
            'res_model': 'account.tax.group',
            'view_mode': 'list',
            'context': {
                'default_country_id': self.account_fiscal_country_id.id,
                'search_default_country_id': self.account_fiscal_country_id.id,
            },
        }

    @api.depends('account_tax_periodicity', 'company_id', 'fiscalyear_last_day', 'fiscalyear_last_month')
    def _compute_account_reports_show_per_company_setting(self):
        custom_start_country_codes = self._get_country_codes_with_another_tax_closing_start_date()
        countries = self.env['account.fiscal.position'].search([
            ('company_id', '=', self.env.company.id),
            ('foreign_vat', '!=', False),
        ]).mapped('country_id') + self.env.company.account_fiscal_country_id
        countries_to_always_show = bool(set(countries.mapped('code')) & custom_start_country_codes)
        for config_settings in self:
            if countries_to_always_show:
                config_settings.account_reports_show_per_company_setting = True
            else:
                max_last_day = monthrange(fields.Date.today().year, int(config_settings.fiscalyear_last_month))[1]
                if config_settings.account_tax_periodicity == 'monthly':
                    config_settings.account_reports_show_per_company_setting = max_last_day != config_settings.fiscalyear_last_day
                else:
                    config_settings.account_reports_show_per_company_setting = config_settings.fiscalyear_last_month != '12' or config_settings.fiscalyear_last_day != max_last_day

    def open_company_dependent_report_settings(self):
        self.ensure_one()
        generic_tax_report = self.env.ref('account.generic_tax_report')
        available_reports = generic_tax_report._get_variants(generic_tax_report.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Configure your start dates'),
            'res_model': 'account.report',
            'domain': [('id', 'in', available_reports.ids)],
            'views': [(self.env.ref('account_reports.account_report_tree_configure_start_dates').id, 'list')]
        }

    def _get_country_codes_with_another_tax_closing_start_date(self):
        """
        To be overridden by specific countries that wants this

        Used to know which countries can have specific start dates settings on reports

        :returns set(str):   A set of country codes from which the start date settings should be shown
        """
        return set()
