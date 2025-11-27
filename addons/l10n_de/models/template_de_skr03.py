# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, Command
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('de_skr03')
    def _get_de_skr03_template_data(self):
        return {
            'code_digits': '4',
            'property_account_receivable_id': 'account_1410',
            'property_account_payable_id': 'account_1610',
            'property_stock_valuation_account_id': 'account_3960',
            'name': 'German Chart of Accounts SKR03',
        }

    @template('de_skr03', 'res.company')
    def _get_de_skr03_res_company(self):
        return {
            self.env.company.id: {
                'account_fiscal_country_id': 'base.de',
                'bank_account_code_prefix': '120',
                'cash_account_code_prefix': '100',
                'transfer_account_code_prefix': '1360',
                'account_default_pos_receivable_account_id': 'account_1411',
                'income_currency_exchange_account_id': 'account_2660',
                'expense_currency_exchange_account_id': 'account_2150',
                'account_journal_early_pay_discount_loss_account_id': 'account_2130',
                'account_journal_early_pay_discount_gain_account_id': 'account_2670',
                'account_sale_tax_id': 'tax_ust_19_skr03',
                'account_purchase_tax_id': 'tax_vst_19_skr03',
                'expense_account_id': 'account_3400',
                'income_account_id': 'account_8400',
                'account_stock_valuation_id': 'account_7200',
            },
        }

    @template('de_skr03', 'account.reconcile.model')
    def _get_de_skr03_reconcile_model(self):
        return {
            'reconcile_3731': {
                'name': 'Discount-EK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_3731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_7_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-7%',
                    }),
                ],
            },
            'reconcile_3736': {
                'name': 'Discount-EK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_3736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_vst_19_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-EK-19%',
                    }),
                ],
            },
            'reconcile_8731': {
                'name': 'Discount-VK-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_8731',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-7%',
                    }),
                ],
            },
            'reconcile_8736': {
                'name': 'Discount-VK-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_8736',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Discount-VK-19%',
                    }),
                ],
            },
            'reconcile_2401': {
                'name': 'Loss of receivables-7%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_2401',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_7_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-7%',
                    }),
                ],
            },
            'reconcile_2406': {
                'name': 'Loss of receivables-19%',
                'line_ids': [
                    Command.create({
                        'account_id': 'account_2406',
                        'amount_type': 'percentage',
                        'tax_ids': [
                            Command.set([
                                'tax_ust_19_skr03',
                            ]),
                        ],
                        'amount_string': '100',
                        'label': 'Loss of receivables-19%',
                    }),
                ],
            },
        }

    @template('de_skr03', 'account.account')
    def _get_de_skr03_account_account(self):
        return {
            'account_7200': {
                'account_stock_expense_id': 'account_3000',
                'account_stock_variation_id': 'account_3955',
            },
            'account_0025': {'asset_model_ids': "asset_other_rights_and_assets"},
            'account_0027': {'asset_model_ids': "asset_computer_software"},
            'account_0030': {'asset_model_ids': "asset_licences_in_industrial_and_similar_rights"},
            'account_0035': {'asset_model_ids': "asset_goodwill"},
            'account_0090': {'asset_model_ids': "asset_commercial_buildings_ol"},
            'account_0100': {'asset_model_ids': "asset_industrial_buildings_ol"},
            'account_0110': {'asset_model_ids': "asset_garages_commercial_ol"},
            'account_0111': {'asset_model_ids': "asset_outdoor_facilities_commercial_ol"},
            'account_0112': {'asset_model_ids': "asset_paved_courtyards_commercial_ol"},
            'account_0113': {'asset_model_ids': "asset_fixtures_in_commercial_and_industrial_buildings_ol"},
            'account_0115': {'asset_model_ids': "asset_other_buildings_commercial_ol"},
            'account_0140': {'asset_model_ids': "asset_residential_buildings_ol"},
            'account_0145': {'asset_model_ids': "asset_garages_residential_ol"},
            'account_0146': {'asset_model_ids': "asset_outdoor_facilities_residential_ol"},
            'account_0147': {'asset_model_ids': "asset_paved_courtyards_residential_ol"},
            'account_0148': {'asset_model_ids': "asset_fixtures_in_residential_buildings_ol"},
            'account_0165': {'asset_model_ids': "asset_commercial_buildings_tp"},
            'account_0170': {'asset_model_ids': "asset_industrial_buildings_tp"},
            'account_0175': {'asset_model_ids': "asset_garages_commercial_tp"},
            'account_0176': {'asset_model_ids': "asset_outdoor_facilities_commercial_tp"},
            'account_0177': {'asset_model_ids': "asset_paved_courtyards_commercial_tp"},
            'account_0178': {'asset_model_ids': "asset_fixtures_in_commercial_and_industrial_buildings_tp"},
            'account_0179': {'asset_model_ids': "asset_other_buildings_commercial_tp"},
            'account_0190': {'asset_model_ids': "asset_residential_buildings_tp"},
            'account_0191': {'asset_model_ids': "asset_garages_residential_tp"},
            'account_0192': {'asset_model_ids': "asset_outdoor_facilities_residential_tp"},
            'account_0193': {'asset_model_ids': "asset_paved_courtyards_residential_tp"},
            'account_0194': {'asset_model_ids': "asset_fixtures_in_residential_buildings_tp"},
            'account_0210': {'asset_model_ids': "asset_machinery"},
            'account_0220': {'asset_model_ids': "asset_machine_tools"},
            'account_0260': {'asset_model_ids': "asset_transportation"},
            'account_0280': {'asset_model_ids': "asset_operating_facilities"},
            'account_0320': {'asset_model_ids': "asset_passenger_cars"},
            'account_0350': {'asset_model_ids': "asset_heavy_goods_vehicles"},
            'account_0380': {'asset_model_ids': "asset_other_transportation_resources"},
            'account_03801': {'asset_model_ids': "asset_motorbike"},
            'account_03802': {'asset_model_ids': "asset_e_bike"},
            'account_03803': {'asset_model_ids': "asset_trailer"},
            'account_03804': {'asset_model_ids': "asset_bicycle"},
            'account_0410': {'asset_model_ids': "asset_office_equipment"},
            'account_04101': {'asset_model_ids': "asset_coffee_machine"},
            'account_04102': {'asset_model_ids': "asset_printer"},
            'account_0420': {'asset_model_ids': "asset_office_fittings"},
            'account_0430': {'asset_model_ids': "asset_shop_fittings"},
            'account_0440': {'asset_model_ids': "asset_tools"},
            'account_0460': {'asset_model_ids': "asset_scaffolding_and_fromwork_materials"},
            'account_0480': {'asset_model_ids': "asset_low_value_assets"},
            'account_0485': {'asset_model_ids': "asset_collective_item"},
        }
