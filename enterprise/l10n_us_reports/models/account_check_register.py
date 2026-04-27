# -*- coding: utf-8 -*-
from odoo import models, api, _


class USReportCustomHandler(models.AbstractModel):
    '''Check Register is an accounting report usually part of the general ledger, used to record
    financial transactions in cash.
    '''
    _name = 'l10n_us.report.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'US Report Custom Handler'

    def _get_custom_display_config(self):
        return {
            'templates': {
                'AccountReportLineName': 'l10n_us_reports.CheckRegisterLineName',
            },
        }

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        return self.env['account.general.ledger.report.handler']._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=warnings)

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options=previous_options)
        report._init_options_journals(options, previous_options=previous_options, additional_journals_domain=[('type', 'in', ('bank', 'cash', 'general'))])
