from odoo import models


class AccountFollowupCustomHandler(models.AbstractModel):
    _inherit = 'account.followup.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if options['export_mode'] == 'print':
            # When printing the report, we don't want to include `no_followup` lines.
            options['forced_domain'] = options.get('forced_domain', []) + [('no_followup', '=', False)]

    def _get_custom_display_config(self):
        config = super()._get_custom_display_config()
        config['components']['AccountReportLine'] = 'account_no_followup.PartnerLedgerFollowupLine'
        config['templates']['AccountReportHeader'] = 'account_no_followup.PartnerLedgerFollowupHeader'
        return config
