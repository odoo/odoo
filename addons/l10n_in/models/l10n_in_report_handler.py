from odoo import models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _init_options_buttons(self, options, previous_options):
        super()._init_options_buttons(options, previous_options)
        company = self.env.company
        generic_report_id = self.env.ref('account.generic_tax_report').id

        # Remove 'Returns' button from generic report for indian company
        if company.country_id.code == 'IN' and self.id == generic_report_id and not self.root_report_id:
            options['buttons'] = [
                button for button in options['buttons']
                if button.get('action') != 'action_open_returns'
            ]
