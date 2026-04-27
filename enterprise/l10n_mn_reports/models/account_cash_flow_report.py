# -*- coding: utf-8 -*-
from odoo import models, _


class MNCashFlowReportCustomHandler(models.AbstractModel):
    _name = 'l10n_mn.cash.flow.report.handler'
    _inherit = 'account.cash.flow.report.handler'
    _description = 'Mongolian Cash Flow Report Custom Handler'

    def _dispatch_aml_data(self, tags_ids, aml_data, layout_data, report_data):
        # OVERRIDE account_reports/models/account_cash_flow_report.py
        # Dispatch the aml_data in the correct layout_line

        layout_line = tags_ids.get(aml_data['account_tag_id'], {'in': 'unclassified_activities_cash_in', 'out': 'unclassified_activities_cash_out'})

        if isinstance(layout_line, dict):
            cash_flow_direction = 'in' if aml_data['balance'] > 0 else 'out'
            layout_line = layout_line[cash_flow_direction]

        self._add_report_data(layout_line, aml_data, layout_data, report_data)

    def _get_tags_ids(self):
        # OVERRIDE account_reports/models/account_cash_flow_report.py
        return {
            self.env.ref('l10n_mn.account_cashflow_tag_111').id: 'cashflow_line_111',
            self.env.ref('l10n_mn.account_cashflow_tag_112').id: 'cashflow_line_112',
            self.env.ref('l10n_mn.account_cashflow_tag_113').id: 'cashflow_line_113',
            self.env.ref('l10n_mn.account_cashflow_tag_114').id: 'cashflow_line_114',
            self.env.ref('l10n_mn.account_cashflow_tag_115').id: 'cashflow_line_115',
            self.env.ref('l10n_mn.account_cashflow_tag_116').id: 'cashflow_line_116',

            self.env.ref('l10n_mn.account_cashflow_tag_121').id: 'cashflow_line_121',
            self.env.ref('l10n_mn.account_cashflow_tag_122').id: 'cashflow_line_122',
            self.env.ref('l10n_mn.account_cashflow_tag_123').id: 'cashflow_line_123',
            self.env.ref('l10n_mn.account_cashflow_tag_124').id: 'cashflow_line_124',
            self.env.ref('l10n_mn.account_cashflow_tag_125').id: 'cashflow_line_125',
            self.env.ref('l10n_mn.account_cashflow_tag_126').id: 'cashflow_line_126',
            self.env.ref('l10n_mn.account_cashflow_tag_127').id: 'cashflow_line_127',
            self.env.ref('l10n_mn.account_cashflow_tag_128').id: 'cashflow_line_128',
            self.env.ref('l10n_mn.account_cashflow_tag_129').id: 'cashflow_line_129',

            self.env.ref('l10n_mn.account_cashflow_tag_211_221').id: {'in': 'cashflow_line_211', 'out': 'cashflow_line_221'},
            self.env.ref('l10n_mn.account_cashflow_tag_212_222').id: {'in': 'cashflow_line_212', 'out': 'cashflow_line_222'},
            self.env.ref('l10n_mn.account_cashflow_tag_213_223').id: {'in': 'cashflow_line_213', 'out': 'cashflow_line_223'},
            self.env.ref('l10n_mn.account_cashflow_tag_214_224').id: {'in': 'cashflow_line_214', 'out': 'cashflow_line_224'},
            self.env.ref('l10n_mn.account_cashflow_tag_215_225').id: {'in': 'cashflow_line_215', 'out': 'cashflow_line_225'},
            self.env.ref('l10n_mn.account_cashflow_tag_216').id: 'cashflow_line_216',
            self.env.ref('l10n_mn.account_cashflow_tag_217').id: 'cashflow_line_217',

            self.env.ref('l10n_mn.account_cashflow_tag_311_321').id: {'in': 'cashflow_line_311', 'out': 'cashflow_line_321'},
            self.env.ref('l10n_mn.account_cashflow_tag_312_323').id: {'in': 'cashflow_line_312', 'out': 'cashflow_line_323'},
            self.env.ref('l10n_mn.account_cashflow_tag_313').id: 'cashflow_line_313',

            self.env.ref('l10n_mn.account_cashflow_tag_322').id: 'cashflow_line_322',
            self.env.ref('l10n_mn.account_cashflow_tag_324').id: 'cashflow_line_324',
            self.env.ref('l10n_mn.account_cashflow_tag_325').id: 'cashflow_line_325',

            self.env.ref('l10n_mn.account_cashflow_tag_400').id: 'cashflow_line_4',
        }

    def _get_cashflow_tag_ids(self):
        # OVERRIDE account_reports/models/account_cash_flow_report.py
        return self._get_tags_ids().keys()

    def _get_layout_data(self):
        # OVERRIDE account_reports/models/account_cash_flow_report.py
        # Indentation of the following dict reflects the structure of the report.
        return {
            'net_increase': {'name': _('All net cash flows'), 'level': 0},
                'cashflow_line_1': {'name': _('1 Cash flow from operating activities'), 'level': 0, 'parent_line_id': 'net_increase'},
                    'cashflow_line_11': {'name': _('1.1 Cash income total (+)'), 'level': 2, 'parent_line_id': 'cashflow_line_1'},
                        'cashflow_line_111': {'name': _('1.1.1 Income from the sale of goods and services'), 'level': 3, 'parent_line_id': 'cashflow_line_11'},
                        'cashflow_line_112': {'name': _('1.1.2 Revenue from rights commissions, fees and payments'), 'level': 3, 'parent_line_id': 'cashflow_line_11'},
                        'cashflow_line_113': {'name': _('1.1.3 Money received from the insured spouse'), 'level': 3, 'parent_line_id': 'cashflow_line_11'},
                        'cashflow_line_114': {'name': _('1.1.4 Tax refunds'), 'level': 3, 'parent_line_id': 'cashflow_line_11'},
                        'cashflow_line_115': {'name': _('1.1.5 Subsidy and financing income'), 'level': 3, 'parent_line_id': 'cashflow_line_11'},
                        'cashflow_line_116': {'name': _('1.1.6 Other cash income'), 'level': 3, 'parent_line_id': 'cashflow_line_11'},
                    'cashflow_line_12': {'name': _('1.2 Amount of monetary expenditure (-)'), 'level': 2, 'parent_line_id': 'cashflow_line_1'},
                        'cashflow_line_121': {'name': _('1.2.1 Paid to Employees'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_122': {'name': _('1.2.2 Paid to the Social Insurance Institution'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_123': {'name': _('1.2.3 Paid for the purchase of inventory'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_124': {'name': _('1.2.4 Paid for Operating Expenses'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_125': {'name': _('1.2.5 Paid for fuel, transportation fees, and spare parts'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_126': {'name': _('1.2.6 Interest paid'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_127': {'name': _('1.2.7 Paid to the tax authorities'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_128': {'name': _('1.2.8 Paid for insurance'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                        'cashflow_line_129': {'name': _('1.2.9 Other monetary expenses'), 'level': 3, 'parent_line_id': 'cashflow_line_12'},
                'cashflow_line_2': {'name': _('2 Cash flows from investing activities'), 'level': 0, 'parent_line_id': 'net_increase'},
                    'cashflow_line_21': {'name': _('2.1 Amount of cash income (+)'), 'level': 2, 'parent_line_id': 'cashflow_line_2'},
                        'cashflow_line_211': {'name': _('2.1.1 Income from sale of fixed assets'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                        'cashflow_line_212': {'name': _('2.1.2 Income from the sale of intangible assets'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                        'cashflow_line_213': {'name': _('2.1.3 Income from sale of investments'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                        'cashflow_line_214': {'name': _('2.1.4 Income from the sale of other long-term assets'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                        'cashflow_line_215': {'name': _('2.1.5 Repayment of loans and cash advances granted to others'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                        'cashflow_line_216': {'name': _('2.1.6 Interest income received'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                        'cashflow_line_217': {'name': _('2.1.7 Dividends Received'), 'level': 3, 'parent_line_id': 'cashflow_line_21'},
                    'cashflow_line_22': {'name': _('2.2 Amount of monetary expenditure (-)'), 'level': 2, 'parent_line_id': 'cashflow_line_2'},
                        'cashflow_line_221': {'name': _('2.2.1 Paid for acquisition and possession of fixed assets'), 'level': 3, 'parent_line_id': 'cashflow_line_22'},
                        'cashflow_line_222': {'name': _('2.2.2 Paid for the acquisition and possession of intangible assets'), 'level': 3, 'parent_line_id': 'cashflow_line_22'},
                        'cashflow_line_223': {'name': _('2.2.3 Paid for acquisition of investment'), 'level': 3, 'parent_line_id': 'cashflow_line_22'},
                        'cashflow_line_224': {'name': _('2.2.4 Paid for the acquisition and possession of other long-term assets'), 'level': 3, 'parent_line_id': 'cashflow_line_22'},
                        'cashflow_line_225': {'name': _('2.2.5 Loans and advances to others'), 'level': 3, 'parent_line_id': 'cashflow_line_22'},
                'cashflow_line_3': {'name': _('3 Cash flow from financing activities'), 'level': 0, 'parent_line_id': 'net_increase'},
                    'cashflow_line_31': {'name': _('3.1 Amount of cash income (+)'), 'level': 2, 'parent_line_id': 'cashflow_line_3'},
                        'cashflow_line_311': {'name': _('3.1.1 Received from borrowing and issuing debt securities'), 'level': 3, 'parent_line_id': 'cashflow_line_31'},
                        'cashflow_line_312': {'name': _('3.1.2 Received from the issuance of shares and other equity securities'), 'level': 3, 'parent_line_id': 'cashflow_line_31'},
                        'cashflow_line_313': {'name': _('3.1.3 Miscellaneous Donations'), 'level': 3, 'parent_line_id': 'cashflow_line_31'},
                    'cashflow_line_32': {'name': _('3.2 Amount of monetary expenditure (-)'), 'level': 2, 'parent_line_id': 'cashflow_line_3'},
                        'cashflow_line_321': {'name': _('3.2.1 Amounts paid for loans and debt securities'), 'level': 3, 'parent_line_id': 'cashflow_line_32'},
                        'cashflow_line_322': {'name': _('3.2.2 Payables for finance leases'), 'level': 3, 'parent_line_id': 'cashflow_line_32'},
                        'cashflow_line_323': {'name': _('3.2.3 Paid for repurchase of shares'), 'level': 3, 'parent_line_id': 'cashflow_line_32'},
                        'cashflow_line_324': {'name': _('3.2.4 Dividends Paid'), 'level': 3, 'parent_line_id': 'cashflow_line_32'},
                        'cashflow_line_325': {'name': _('3.2.5 Various donations, assistance and fines paid'), 'level': 3, 'parent_line_id': 'cashflow_line_32'},
                'cashflow_line_4': {'name': _('Exchange rate differences'), 'level': 0, 'parent_line_id': 'net_increase'},
                'unclassified_activities': {'name': _('Cash flows from unclassified activities'), 'level': 0, 'parent_line_id': 'net_increase'},
                    'unclassified_activities_cash_in': {'name': _('Cash in'), 'level': 3, 'parent_line_id': 'unclassified_activities'},
                    'unclassified_activities_cash_out': {'name': _('Cash out'), 'level': 3, 'parent_line_id': 'unclassified_activities'},
            'opening_balance': {'name': _('Initial balance of cash and cash equivalents'), 'level': 0},
            'closing_balance': {'name': _('Closing balance of cash and cash equivalents'), 'level': 0},
        }
