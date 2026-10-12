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
