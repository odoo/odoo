# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)

class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in')
    def _get_in_template_data(self):
        return {
            'name': "Basic",
            'property_account_receivable_id': 'p10040',
            'property_account_payable_id': 'p11211',
            'code_digits': '6',
            'display_invoice_amount_total_words': True,
        }

    @template('in', 'res.company')
    def _get_in_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.in',
                'bank_account_code_prefix': '1002',
                'cash_account_code_prefix': '1001',
                'transfer_account_code_prefix': '1008',
                'account_default_pos_receivable_account_id': 'p10041',
                'income_currency_exchange_account_id': 'p2013',
                'expense_currency_exchange_account_id': 'p2117',
                'account_journal_early_pay_discount_loss_account_id': 'p2132',
                'account_journal_early_pay_discount_gain_account_id': '2012',
                'deferred_expense_account_id': 'p10084',
                'deferred_revenue_account_id': 'p10085',
                'expense_account_id': 'p2107',
                'income_account_id': 'p20011',
                'l10n_in_withholding_account_id': 'p100595',
            },
        }

    @template('in', 'account.cash.rounding')
    def _get_in_account_cash_rounding(self):
        return {
            'l10n_in.cash_rounding_in_half_up': {
                'profit_account_id': 'p213202',
                'loss_account_id': 'p213201',
            }
        }

    def _load(self, template_code, company, install_demo):
        transition_rules = {
            ("in", "in_adv"): {"context_update": {"skip_unlink": True}},
            ("in_adv", "in"): {"error": _("You cannot switch from the advanced chart template back to the basic chart template.")},
        }
        rule = transition_rules.get((company.chart_template, template_code), {})
        self = self.with_context(**rule.get("context_update", {}))
        if "error" in rule:
            raise UserError(rule["error"])
        return super()._load(template_code, company, install_demo)
