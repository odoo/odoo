from odoo import Command, models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('in')
    def _get_in_template_data(self):
        return {
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
                'fiscalyear_last_month': '3',
                'account_sale_tax_id': 'sgst_sale_5',
                'account_purchase_tax_id': 'sgst_purchase_5',
                'deferred_expense_account_id': 'p10084',
                'deferred_revenue_account_id': 'p10085',
                'expense_account_id': 'p2107',
                'income_account_id': 'p20011',
                'l10n_in_withholding_account_id': 'p100595',
                'tax_calculation_rounding_method': 'round_per_line',
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

    @template('in', 'account.fiscal.position')
    def _get_in_account_fiscal_position(self):
        _ = self.env._
        company = self.env.company
        state_ids = [Command.set(company.state_id.ids)] if company.state_id else False
        intra_state_name = company.state_id and _("Within %s", company.state_id.name) or _("Intra State")
        country_in_id = self.env.ref('base.in').id
        state_specific = {
            'fiscal_position_in_intra_state': {
                'name': intra_state_name,
                'sequence': 1,
                'auto_apply': True,
                'state_ids': state_ids,
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_intra_state'),
                'country_id': country_in_id,
            },
            'fiscal_position_in_inter_state': {
                'name': _("Inter State"),
                'sequence': 2,
                'auto_apply': True,
                'country_group_id': 'l10n_in.inter_state_group',
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_inter_state'),
            },
        }
        if company.parent_id:
            return {
                self.company_xmlid(k): v
                for k, v in state_specific.items()
            }
        return {
            **state_specific,
            'fiscal_position_in_sez': {
                'name': _("Special Economic Zone (SEZ)"),
                'sequence': 3,
                'auto_apply': True,
                'state_ids': [Command.set(self.env.ref('l10n_in.state_in_oc').ids)],
                'country_id': country_in_id,
                'note': _("SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS ON PAYMENT OF INTEGRATED TAX."),
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_inter_state'),
            },
            'fiscal_position_in_export_sez_in': {
                'name': _("Export"),
                'sequence': 4,
                'auto_apply': True,
                'note': _("SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS ON PAYMENT OF INTEGRATED TAX."),
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_export_sez_in'),
            },
            'fiscal_position_in_lut_sez_1': {
                'name': _("SEZ - LUT (WOP)"),
                'sequence': 5,
                'state_ids': [Command.set(self.env.ref('l10n_in.state_in_oc').ids)],
                'country_id': country_in_id,
                'note': _("SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS UNDER BOND OR LETTER OF UNDERTAKING WITHOUT PAYMENT OF INTEGRATED TAX."),
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_lut_sez_1'),
            },
            'fiscal_position_in_lut_sez': {
                'name': _("Export - LUT (WOP)"),
                'sequence': 6,
                'note': _('SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS UNDER BOND OR LETTER OF UNDERTAKING WITHOUT PAYMENT OF INTEGRATED TAX.'),
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_lut_sez'),
            },
        }

    def _get_l10n_in_fiscal_tax_vals(self, fiscal_position_xml_ids):
        rates = [1, 2, 5, 12, 18, 28, 40]
        taxes_xml_ids = []

        if fiscal_position_xml_ids == 'fiscal_position_in_intra_state':
            taxes_xml_ids = [f"sgst_{tax_type}_{rate}" for tax_type in ["sale", "purchase"] for rate in rates]
        elif fiscal_position_xml_ids == 'fiscal_position_in_inter_state':
            taxes_xml_ids = [f"igst_{tax_type}_{rate}" for tax_type in ["sale", "purchase"] for rate in rates]
        elif fiscal_position_xml_ids == 'fiscal_position_in_export_sez_in':
            taxes_xml_ids = [f"igst_sale_{rate}_sez_exp" for rate in rates] + [f"igst_purchase_{rate}" for rate in rates] + ['igst_sale_0_sez_exp']
        elif fiscal_position_xml_ids == 'fiscal_position_in_lut_sez':
            taxes_xml_ids = [f"igst_sale_{rate}_sez_exp_lut" for rate in rates] + ['igst_sale_0_sez_exp_lut']
        elif fiscal_position_xml_ids == 'fiscal_position_in_lut_sez_1':
            taxes_xml_ids = [f"igst_sale_{rate}_sez_lut" for rate in rates] + ['igst_sale_0_sez_lut']
        return [Command.set(taxes_xml_ids)]

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'in':
            company = company or self.env.company
            company._update_l10n_in_is_gst_registered()

            # The COA (Chart of Accounts) data is loaded after the initial compute methods are called.
            # During initial journal setup, the payment methods and accounts may not exist yet,
            # causing the payment method lines to not be properly configured.
            # We call these helper methods again in _post_load_data to ensure all payment method lines
            # are correctly assigned once all COA data is fully available.
            bank_journals = company.bank_journal_ids
            bank_journals._update_payment_method_lines("inbound")
            bank_journals._update_payment_method_lines("outbound")
