from odoo import  Command, _, models, fields
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
        company = self.env.company
        state_ids = [Command.set(company.state_id.ids)] if company.state_id else False
        intra_state_name = company.state_id and _('Within %s', company.state_id.name) or _('Intra State')
        state_specific = {
            'fiscal_position_in_intra_state': {
                'name': intra_state_name,
                'sequence': 1,
                'auto_apply': True,
                'state_ids': state_ids,
                'country_id': self.env.ref('base.in').id,
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_intra_state'),
            },
            'fiscal_position_in_inter_state': {
                'name': _('Inter State'),
                'sequence': 2,
                'auto_apply': True,
                'country_group_id': 'l10n_in.inter_state_group',
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_inter_state'),
            },
        }
        if company.parent_id:
            return state_specific
        return {
            **state_specific,
            'fiscal_position_in_export_sez_in': {
                'name': _('Export/SEZ'),
                'sequence': 3,
                'auto_apply': True,
                'note': _('SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS ON PAYMENT OF INTEGRATED TAX.'),
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_export_sez_in'),
            },
            'fiscal_position_in_lut_sez': {
                'name': _('LUT - Export/SEZ'),
                'sequence': 4,
                'note': _('SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS UNDER BOND OR LETTER OF UNDERTAKING WITHOUT PAYMENT OF INTEGRATED TAX.'),
                'tax_ids': self._get_l10n_in_fiscal_tax_vals('fiscal_position_in_lut_sez'),
            },
        }

    def _get_l10n_in_fiscal_tax_vals(self, fiscal_position_xml_ids):
        rates = [1, 2, 5, 12, 18, 28]
        taxes_xml_ids = []

        if fiscal_position_xml_ids == 'fiscal_position_in_intra_state':
            taxes_xml_ids = [f"sgst_{tax_type}_{rate}" for tax_type in ["sale", "purchase"] for rate in rates]
        elif fiscal_position_xml_ids == 'fiscal_position_in_inter_state':
            taxes_xml_ids = [f"igst_{tax_type}_{rate}" for tax_type in ["sale", "purchase"] for rate in rates]
        elif fiscal_position_xml_ids == 'fiscal_position_in_export_sez_in':
            taxes_xml_ids = [f"igst_sale_{rate}_sez_exp" for rate in rates] + [f"igst_purchase_{rate}" for rate in rates] + ['igst_sale_0_sez_exp']
        elif fiscal_position_xml_ids == 'fiscal_position_in_lut_sez':
            taxes_xml_ids = [f"igst_sale_{rate}_sez_exp_lut" for rate in rates] + ['igst_sale_0_sez_exp_lut']
        return [Command.set(taxes_xml_ids)]

    def _set_l10n_in_default_outstanding_payment_accounts(self, company, bank_journal=None, pay_type=None):
        if bank_journal := bank_journal or self.env.ref(f"account.{company.id}_bank", raise_if_not_found=False):
            payment_account_map = {
                "inbound": (
                    "account.account_payment_method_manual_in",
                    f"account.{company.id}_account_journal_payment_debit_account_id",
                ),
                "outbound": (
                    "account.account_payment_method_manual_out",
                    f"account.{company.id}_account_journal_payment_credit_account_id",
                ),
            }

            for ptype in ([pay_type] if pay_type in payment_account_map else payment_account_map.keys()):
                method_xmlid, account_xmlid = payment_account_map[ptype]
                if ((method := self.env.ref(method_xmlid, raise_if_not_found=False)) and
                    (account_ref := self.env.ref(account_xmlid, raise_if_not_found=False))):
                    method_line = bank_journal[f"{ptype}_payment_method_line_ids"].filtered(lambda l: l.payment_method_id == method)
                    if method_line:
                        method_line.payment_account_id = account_ref

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'in':
            company = company or self.env.company
            company._update_l10n_in_is_gst_registered()

            self._set_l10n_in_default_outstanding_payment_accounts(company)
