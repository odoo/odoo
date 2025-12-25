# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('de_skr04')
    def _get_de_skr04_template_data(self):
        return {
            'name': 'German chart of accounts SKR04',
            'code_digits': '4',
            'property_account_receivable_id': 'chart_skr04_1205',
            'property_account_payable_id': 'chart_skr04_3301',
        }

    @template('de_skr04', 'res.company')
    def _get_de_skr04_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.de',
                'bank_account_code_prefix': '180',
                'cash_account_code_prefix': '160',
                'transfer_account_code_prefix': '1460',
                'account_default_pos_receivable_account_id': 'chart_skr04_1206',
                'income_currency_exchange_account_id': 'chart_skr04_4840',
                'expense_currency_exchange_account_id': 'chart_skr04_6880',
                'account_journal_early_pay_discount_loss_account_id': 'chart_skr04_4730',
                'account_journal_early_pay_discount_gain_account_id': 'chart_skr04_5730',
                'default_cash_difference_income_account_id': 'chart_skr04_9991',
                'default_cash_difference_expense_account_id': 'chart_skr04_9994',
                'account_sale_tax_id': 'tax_ust_19_skr04',
                'account_purchase_tax_id': 'tax_vst_19_skr04',
                'expense_account_id': 'chart_skr04_5400',
                'income_account_id': 'chart_skr04_4400',
                'account_stock_valuation_id': 'chart_skr04_1000',
            },
        }

    @template('de_skr04', 'account.reconcile.model')
    def _get_de_skr04_reconcile_model(self):
        return {
            'reconcile_5731': {
                'name': 'Discount-EK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_5731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_7_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-7%',
                    }),
                ],
            },
            'reconcile_5736': {
                'name': 'Discount-EK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_5736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_19_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-19%',
                    }),
                ],
            },
            'reconcile_4731': {
                'name': 'Skonto-VK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_4731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-7%',
                    }),
                ],
            },
            'reconcile_4736': {
                'name': 'Discount-VK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_4736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-19%',
                    }),
                ],
            },
            'reconcile_6931': {
                'name': 'Loss of receivables-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_6931',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-7%',
                    }),
                ],
            },
            'reconcile_6936': {
                'name': 'Loss of receivables-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'chart_skr04_6936',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr04',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-19%',
                    }),
                ],
            },
        }

    @template('de_skr04', 'account.account')
    def _get_de_skr04_account_account(self):
        return {
            'chart_skr04_1000': {
                'account_stock_expense_id': 'chart_skr04_5000',
                'account_stock_variation_id': 'chart_skr04_5880',
            },
            'chart_skr04_130': {'asset_model_ids': "asset_skr04_other_rights_and_assets"},
            'chart_skr04_135': {'asset_model_ids': "asset_skr04_computer_software"},
            'chart_skr04_140': {'asset_model_ids': "asset_skr04_licences_in_industrial_and_similar_rigts"},
            'chart_skr04_150': {'asset_model_ids': "asset_skr04_goodwill"},
            'chart_skr04_240': {'asset_model_ids': "asset_skr04_commercial_buildings_ol"},
            'chart_skr04_250': {'asset_model_ids': "asset_skr04_industrial_buildings_ol"},
            'chart_skr04_260': {'asset_model_ids': "asset_skr04_other_buildings_commercial_ol"},
            'chart_skr04_270': {'asset_model_ids': "asset_skr04_garages_commercial_ol"},
            'chart_skr04_280': {'asset_model_ids': "asset_skr04_outdoor_facilities_commercial_ol"},
            'chart_skr04_285': {'asset_model_ids': "asset_skr04_paved_courtyards_commercial_ol"},
            'chart_skr04_290': {'asset_model_ids': "asset_skr04_fixtures_in_commercial_and_industrial_buildings_ol"},
            'chart_skr04_300': {'asset_model_ids': "asset_skr04_residential_buildings_ol"},
            'chart_skr04_305': {'asset_model_ids': "asset_skr04_garages_residential_ol"},
            'chart_skr04_310': {'asset_model_ids': "asset_skr04_outdoor_facilities_residential_ol"},
            'chart_skr04_315': {'asset_model_ids': "asset_skr04_paved_courtyards_residential_ol"},
            'chart_skr04_320': {'asset_model_ids': "asset_skr04_fixtures_in_residential_buildings_ol"},
            'chart_skr04_340': {'asset_model_ids': "asset_skr04_commercial_buildings_tp"},
            'chart_skr04_350': {'asset_model_ids': "asset_skr04_industrial_buildings_tp"},
            'chart_skr04_360': {'asset_model_ids': "asset_skr04_residential_buildings_tp"},
            'chart_skr04_370': {'asset_model_ids': "asset_skr04_other_buildings_commercial_tp"},
            'chart_skr04_380': {'asset_model_ids': "asset_skr04_garages_commercial_tp"},
            'chart_skr04_390': {'asset_model_ids': "asset_skr04_outdoor_facilities_commercial_tp"},
            'chart_skr04_395': {'asset_model_ids': "asset_skr04_paved_courtyards_commercial_tp"},
            'chart_skr04_398': {'asset_model_ids': "asset_skr04_fixtures_in_commercial_and_industrial_buildings_tp"},
            'chart_skr04_440': {'asset_model_ids': "asset_skr04_machinery"},
            'chart_skr04_450': {'asset_model_ids': "asset_skr04_transportation"},
            'chart_skr04_460': {'asset_model_ids': "asset_skr04_machine_tools"},
            'chart_skr04_470': {'asset_model_ids': "asset_skr04_operating_facilities"},
            'chart_skr04_520': {'asset_model_ids': "asset_skr04_passenger_cars"},
            'chart_skr04_540': {'asset_model_ids': "asset_skr04_heavy_goods_vehicles"},
            'chart_skr04_560': {'asset_model_ids': "asset_skr04_other_transportation_resources"},
            'chart_skr04_5601': {'asset_model_ids': "asset_skr04_motorbike"},
            'chart_skr04_5602': {'asset_model_ids': "asset_skr04_e_bike"},
            'chart_skr04_5603': {'asset_model_ids': "asset_skr04_trailer"},
            'chart_skr04_5604': {'asset_model_ids': "asset_skr04_bicycle"},
            'chart_skr04_620': {'asset_model_ids': "asset_skr04_tools"},
            'chart_skr04_635': {'asset_model_ids': "asset_skr04_office_equipment"},
            'chart_skr04_6351': {'asset_model_ids': "asset_skr04_coffee_machine"},
            'chart_skr04_6352': {'asset_model_ids': "asset_skr04_printer"},
            'chart_skr04_640': {'asset_model_ids': "asset_skr04_shop_fittings"},
            'chart_skr04_650': {'asset_model_ids': "asset_skr04_office_fittings"},
            'chart_skr04_660': {'asset_model_ids': "asset_skr04_scaffolding_and_fromwork_materials"},
            'chart_skr04_670': {'asset_model_ids': "asset_skr04_low_value_assets"},
            'chart_skr04_675': {'asset_model_ids': "asset_skr04_collective_item"},
        }
