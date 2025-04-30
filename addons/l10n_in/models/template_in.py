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
            },
            'fiscal_position_in_inter_state': {
                'name': _('Inter State'),
                'sequence': 2,
                'auto_apply': True,
                'country_group_id': 'l10n_in.inter_state_group',
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
            },
            'fiscal_position_in_lut_sez': {
                'name': _('LUT - Export/SEZ'),
                'sequence': 4,
                'note': _('SUPPLY MEANT FOR EXPORT/SUPPLY TO SEZ UNIT OR SEZ DEVELOPER FOR AUTHORISED OPERATIONS UNDER BOND OR LETTER OF UNDERTAKING WITHOUT PAYMENT OF INTEGRATED TAX.'),
            },
        }

    @template('in', 'account.tax')
    def _get_in_account_tax(self):
        # Tax mappings are dependent on the fiscal positions
        tax_data_generation_settings = [
            ('fiscal_position_in_inter_state', None, False, False),
            ('fiscal_position_in_export_sez_in', '_sez_exp', False, True),
            ('fiscal_position_in_lut_sez', '_sez_exp_lut', True, True),
        ]
        tax_data = {}
        csv_tax_data = self._parse_csv('in', 'account.tax', module='l10n_in')
        fiscal_position_data = self._get_in_account_fiscal_position()
        for xml_id, trailing_id, use_zero_rated_igst, zero_rated_with_igst in tax_data_generation_settings:
            if xml_id in fiscal_position_data:
                extra_taxes = self._get_l10n_in_fiscal_tax_vals(xml_id, use_zero_rated_igst=use_zero_rated_igst, trailing_id=trailing_id, get_zero_rated_with_igst=zero_rated_with_igst)
                tax_data = {
                    **tax_data,
                    **{extrak: extrav for extrak, extrav in extra_taxes.items() if extrak in csv_tax_data},
                }
        return tax_data

    def _get_l10n_in_fiscal_tax_vals(self, fiscal_position_xml_ids, use_zero_rated_igst=False, trailing_id=False, get_zero_rated_with_igst=False):
        tax_data = {
            f"igst_{tax_type}_{0 if use_zero_rated_igst and tax_type == 'purchase' else rate}{(tax_type == 'sale' and trailing_id) or ''}": {
                'fiscal_position_ids': fiscal_position_xml_ids,
                'original_tax_ids': f"sgst_{tax_type}_{rate}",
            }
            for tax_type in ["sale", "purchase"]
            for rate in [1, 2, 5, 8, 12, 18, 28]  # Available existing GST Rates..... 8?!?!?! Do igst_{sale/purchase}_8 taxes even exist?
        }
        # Since the taxes mapped above need to be in the domestic fiscal position
        tax_data = {
            **tax_data,
            **{
                f"sgst_{tax_type}_{rate}": {
                    'fiscal_position_ids': 'fiscal_position_in_intra_state',
                }
                for tax_type in ["sale", "purchase"]
                for rate in [1, 2, 5, 8, 12, 18, 28]
            }
        }

        if get_zero_rated_with_igst:
            tax_data = {
                **tax_data,
                **self._get_l10n_in_zero_rated_with_igst_zero_tax_vals(fiscal_position_xml_ids),
            }
        return tax_data

    def _get_l10n_in_zero_rated_with_igst_zero_tax_vals(self, fiscal_position_xml_ids):
        return {
            "igst_sale_0": {
                'fiscal_position_ids': fiscal_position_xml_ids,
                'original_tax_ids': "exempt_sale,nil_rated_sale",
            }
        }

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        if template_code == 'in':
            company = company or self.env.company
            company._update_l10n_in_is_gst_registered()
