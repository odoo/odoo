# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('es_common')
    def _get_es_common_template_data(self):
        return {
            'name': _('Common'),
            'visible': 0,
        }

    @template('es_common', 'res.company')
    def _get_es_common_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.es',
                'bank_account_code_prefix': '572',
                'cash_account_code_prefix': '570',
                'transfer_account_code_prefix': '57299',
                'account_default_pos_receivable_account_id': 'account_common_4301',
                'income_currency_exchange_account_id': 'account_common_768',
                'expense_currency_exchange_account_id': 'account_common_668',
                'account_journal_suspense_account_id': 'account_common_572998',
                'account_journal_early_pay_discount_loss_account_id': 'account_common_7060',
                'account_journal_early_pay_discount_gain_account_id': 'account_common_6060',
                'default_cash_difference_income_account_id': 'account_common_778',
                'default_cash_difference_expense_account_id': 'account_common_678',
                'deferred_expense_account_id': 'account_common_480',
                'deferred_revenue_account_id': 'account_common_485',
                'expense_account_id': 'account_common_600',
                'income_account_id': 'account_common_7000',
                'receivable_account_id': 'account_common_4300',
                'payable_account_id': 'account_common_4100',
                'account_stock_valuation_id': 'account_common_310',
                'account_sale_tax_id': 'account_tax_template_s_iva21b',
                'account_purchase_tax_id': 'account_tax_template_p_iva21_bc',
            },
        }

    @template('es_common', 'account.journal')
    def _get_es_common_account_journal(self):
        return {
            'purchase': {
                'non_deductible_account_id': 'account_common_544',
            },
        }

    @template('es_common', 'account.account')
    def _get_es_common_account_account(self):
        canary_accounts = self._parse_csv('es_canary_common', 'account.account', module='l10n_es')

        return {
            'account_common_200': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_680',
            },
            'account_common_201': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_680',
            },
            'account_common_202': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_682',
            },
            'account_common_203': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_682',
            },
            'account_common_205': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_682',
            },
            'account_common_206': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_682',
            },
            'account_common_209': {
                'asset_depreciation_account_id': 'account_common_2800',
                'asset_expense_account_id': 'account_common_682',
            },
            'account_common_211': {
                'asset_depreciation_account_id': 'account_common_2811',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_212': {
                'asset_depreciation_account_id': 'account_common_2812',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_213': {
                'asset_depreciation_account_id': 'account_common_2813',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_214': {
                'asset_depreciation_account_id': 'account_common_2814',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_215': {
                'asset_depreciation_account_id': 'account_common_2815',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_216': {
                'asset_depreciation_account_id': 'account_common_2816',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_217': {
                'asset_depreciation_account_id': 'account_common_2817',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_218': {
                'asset_depreciation_account_id': 'account_common_2818',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_219': {
                'asset_depreciation_account_id': 'account_common_2819',
                'asset_expense_account_id': 'account_common_681',
            },
            'account_common_221': {
                'asset_depreciation_account_id': 'account_common_282',
                'asset_expense_account_id': 'account_common_682',
            },
            'account_common_310': {
                'account_stock_expense_id': 'account_common_601',
                'account_stock_variation_id': 'account_common_611',
            },
            **canary_accounts
        }

    @template('es_common', 'account.tax')
    def _get_es_common_account_tax(self):
        mainland_tax_data = self._parse_csv('es_common_mainland', 'account.tax', module='l10n_es')
        canary_tax_data = self._parse_csv('es_canary_common', 'account.tax', module='l10n_es')

        TERRITORY_LINKED_FIELDS = ('fiscal_position_ids', 'original_tax_ids')
        INVARIANT_FIELDS = ('amount', 'amount_type', 'l10n_es_type', 'type_tax_use')

        for xml_id, canary_vals in canary_tax_data.items():
            mainland_vals = mainland_tax_data.get(xml_id)

            if mainland_vals is None:
                continue

            for field in INVARIANT_FIELDS:
                mainland_value = mainland_vals.get(field)
                canary_value = canary_vals.get(field)
                if mainland_value and canary_value and mainland_value != canary_value:
                    raise ValueError(
                        f"El campo '{field}' difiere entre las versiones mainland y canaria "
                        f"de la tax '{xml_id}': {mainland_value!r} vs {canary_value!r}. "
                        "Esto no debería pasar para una tax que se supone idéntica en ambos "
                        "territorios; revisa los CSV 'es_common_mainland' y 'es_canary_common'."
                    )
                if mainland_value and not canary_value:
                    canary_vals[field] = mainland_value

            for field in TERRITORY_LINKED_FIELDS:
                mainland_field_value = mainland_vals.get(field)
                canary_field_value = canary_vals.get(field)
                if mainland_field_value and canary_field_value:
                    canary_vals[field] = f"{mainland_field_value},{canary_field_value}"
                elif mainland_field_value and not canary_field_value:
                    canary_vals[field] = mainland_field_value

        mainland_keys = {
            (vals.get('name'), vals.get('type_tax_use'), vals.get('tax_scope'))
            for xml_id, vals in mainland_tax_data.items()
            if xml_id not in canary_tax_data
        }

        for xml_id, vals in canary_tax_data.items():
            if xml_id in mainland_tax_data:
                continue
            key = (vals.get('name'), vals.get('type_tax_use'), vals.get('tax_scope'))
            if key in mainland_keys:
                vals['name'] = f"{vals['name']} (IGIC)"
            vals['active'] = False

        tax_data = {**mainland_tax_data, **canary_tax_data}
        self._deref_account_tags('es_pymes', tax_data)
        return tax_data

    @template('es_common', 'account.fiscal.position')
    def _get_es_common_account_fiscal_position(self):
        mainland_fp_data = self._parse_csv('es_common_mainland', 'account.fiscal.position', module='l10n_es')
        canary_fp_data = self._parse_csv('es_canary_common', 'account.fiscal.position', module='l10n_es')

        for xml_id, vals in canary_fp_data.items():
            if not isinstance(vals, dict):
                continue
            if not vals.get('country_id') and not vals.get('state_ids'):
                vals.pop('auto_apply', None)

        return {**mainland_fp_data, **canary_fp_data}

    @template('es_common', 'account.tax.group')
    def _get_es_common_account_tax_group(self):
        mainland_group_data = self._parse_csv('es_common_mainland', 'account.tax.group', module='l10n_es')
        canary_group_data = self._parse_csv('es_canary_common', 'account.tax.group', module='l10n_es')
        return {**mainland_group_data, **canary_group_data}
