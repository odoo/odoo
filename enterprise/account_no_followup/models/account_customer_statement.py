from odoo import models


class CustomerStatementCustomHandler(models.AbstractModel):
    _inherit = 'account.customer.statement.report.handler'

    def _get_custom_display_config(self):
        display_config = super()._get_custom_display_config()
        display_config['components']['AccountReportLine'] = 'account_no_followup.PartnerLedgerFollowupLine'
        display_config['templates']['AccountReportHeader'] = 'account_no_followup.PartnerLedgerFollowupHeader'

        return display_config
