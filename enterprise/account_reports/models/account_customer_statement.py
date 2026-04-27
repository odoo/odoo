from odoo import models, _


class CustomerStatementCustomHandler(models.AbstractModel):
    _name = 'account.customer.statement.report.handler'
    _inherit = 'account.partner.ledger.report.handler'
    _description = 'Customer Statement Custom Handler'

    def _get_custom_display_config(self):
        display_config = super()._get_custom_display_config()
        display_config['css_custom_class'] += ' customer_statement'
        if self.env.ref('account_reports.pdf_export_main_customer_report', raise_if_not_found=False):
            display_config.setdefault('pdf_export', {})['pdf_export_main'] = 'account_reports.pdf_export_main_customer_report'
        return display_config

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        options['buttons'].append({
            'name': _('Send'),
            'action': 'action_send_statements',
            'sequence': 90,
            'always_show': True,
        })
