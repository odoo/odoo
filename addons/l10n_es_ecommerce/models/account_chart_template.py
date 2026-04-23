from odoo import models

from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template(model='account.journal')
    def _get_simplified_journal(self, template_code):
        """Add a journal for simplified invoices.

        Its default income account is aligned with the regular Sales journal.
        When that journal isn't available yet (e.g. while gathering the journals
        during the initial chart-template load) we fall back to the company's
        income account, which is exactly what the Sales journal is set to.
        """
        sale_journal = self.ref('sale', raise_if_not_found=False)
        default_account = (
            sale_journal.default_account_id
            if sale_journal
            else self.env.company.income_account_id
        )
        journal_vals = {
            'name': self.env._("Simplified Invoice"),
            'type': 'sale',
            'code': 'SINV',
            'show_on_dashboard': False,
        }
        if default_account:
            journal_vals['default_account_id'] = default_account.id
        return {'simplified_journal': journal_vals}

    @template(model='res.company')
    def _get_simplified_res_company(self, chart_template):
        """Make sure the tax return journal is set on the company.

        This is necessary when the CoA was already installed before this module.
        The method is called in the post-init hook of this module.
        """
        company = self.env.company
        return {
            company.id: {
                'simplified_invoice_journal_id': company.simplified_invoice_journal_id.id or 'simplified_journal',
            },
        }

    def _post_load_data(self, template_code, company, template_data):
        """Align the simplified journal's default income account with the Sales
        journal once every journal has been created. This is the canonical place
        to do it: the base implementation sets the Sales journal account here too,
        so by calling super() first the Sales journal already has its account.
        """
        super()._post_load_data(template_code, company, template_data)
        company = company or self.env.company
        simplified_journal = self.ref('simplified_journal', raise_if_not_found=False)
        if simplified_journal and not simplified_journal.default_account_id:
            sale_journal = self.ref('sale', raise_if_not_found=False)
            simplified_journal.default_account_id = (
                sale_journal.default_account_id or company.income_account_id
            )
