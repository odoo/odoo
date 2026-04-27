# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.osv import expression


class ResPartner(models.Model):
    _inherit = 'res.partner'

    active_company_country_code = fields.Char(compute='_compute_active_company_country_code')

    @api.depends_context('company')
    def _compute_active_company_country_code(self):
        self.active_company_country_code = self.env.company.country_code

    def action_print_report_statement_account(self, options=None):
        domain = []
        date_to = fields.Date.today()
        if options:
            date_to = options.get("date", {}).get("date_to", fields.Date.today())
            domain = expression.AND([
                domain,
                [('date', '<=', date_to)],
                self.env['account.report']._get_options_account_type_domain(options)
            ])
        else:
            domain = expression.AND([domain, [('date', '<=', fields.Date.today())]])
        return self.env.ref('l10n_my_reports.action_report_statement_account').report_action(self, data={
            'date_to': date_to,
            'domain': domain,
        })
