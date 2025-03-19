from datetime import date, timedelta

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon


class TestPointOfSaleDataHttpCommon(AccountTestInvoicingHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        # Delete or archive all data that could interfere with the tests
        self.env['product.template'].search([('available_in_pos', '=', True)]).write({'active': False})
        self.env['pos.session'].sudo().search([]).unlink()
        self.env["pos.category"].search([]).unlink()

        # Ensure access rights
        self.env.user.group_ids += self.env.ref('stock_account.group_stock_accounting_automatic')

        # The order of functions call is important
        self.setup_test_company(self)
        self.setup_test_journals(self)
        self.setup_test_payment_methods(self)
        self.setup_test_partners(self)
        self.setup_test_categories(self)
        self.setup_test_taxes(self)
        self.setup_test_products(self)
        self.setup_test_pricelists(self)
        self.setup_test_pos_config(self)
        self.setup_test_users(self)

    def start_pos_tour(self, tour_name, login="pos_user", **kwargs):
        self.start_tour(f"/pos/ui?config_id={self.pos_config.id}", tour_name, login=login, **kwargs)

    def setup_test_pos_config(self):
        self.env['pos.config'].search([]).unlink()
        self.pos_config = self.env['pos.config'].create({
            'name': 'Main Point of Sale',
            'invoice_journal_id': self.invoice_journal.id,
            'journal_id': self.sale_journal.id,
            'iface_tipproduct': True,
            'ship_later': True,
            'tip_product_id': self.product_tip.id,
            'use_pricelist': True,
            'pricelist_id': self.public_pricelist.id,
            'available_pricelist_ids': [(4, pricelist.id) for pricelist in self.all_pricelists],
            'payment_method_ids': [
                (4, self.credit_payment_method.id),
                (4, self.bank_payment_method.id),
                (4, self.cash_payment_method.id)],
            'fiscal_position_ids': [
                (0, 0, {
                    'name': "FP-POS-2M",
                    'tax_ids': [
                        (0, 0, {
                            'tax_src_id': self.source_tax.id,
                            'tax_dest_id': self.source_tax.id}),
                        (0, 0, {
                            'tax_src_id': self.source_tax.id,
                            'tax_dest_id': self.destination_tax.id}),
                        (0, 0, {
                            'tax_src_id': self.tax_15_include.id,
                            'tax_dest_id': False})
                    ]
                })
            ],
        })

    def setup_test_users(self):
        self.pos_user = self.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_user',
            'password': 'pos_user',
            'group_ids': [
                (4, self.env.ref('base.group_user').id),
                (4, self.env.ref('point_of_sale.group_pos_user').id),
                (4, self.env.ref('stock.group_stock_user').id),
            ],
            'tz': 'America/New_York',
        })
        self.pos_admin = self.env['res.users'].create({
            'name': 'A powerful PoS man!',
            'login': 'pos_admin',
            'password': 'pos_admin',
            'group_ids': [
                (4, self.env.ref('point_of_sale.group_pos_manager').id),
            ],
            'tz': 'America/New_York',
        })
        self.pos_user.partner_id.email = 'pos_user@test.com'
        self.pos_admin.partner_id.email = 'pos_admin@test.com'

    def setup_test_company(self):
        self.first_company = self.company_data['company']
        self.first_company.write({
            'name': 'Point of Sale company',
            'point_of_sale_update_stock_quantities': 'real',
        })

    def setup_test_pricelists(self):
        self.excluded_pricelist = self.env['product.pricelist'].create({
            'name': 'Not loaded'
        })
        self.public_pricelist = self.env['product.pricelist'].create({
            'name': 'Public Pricelist',
        })
        self.fixed_pricelist = self.env['product.pricelist'].create({
            'name': 'Fixed',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_one.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 13.95,  # test for issues like in 7f260ab517ebde634fc274e928eb062463f0d88f
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_two.product_variant_id.id,
            })],
        })
        self.percent_pricelist = self.env['product.pricelist'].create({
            'name': 'Percentage',
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'percent_price': 100,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_one.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'percentage',
                'percent_price': 99,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_two.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'percentage',
                'percent_price': 0,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_three.product_variant_id.id,
            })],
        })
        self.formula_pricelist = self.env['product.pricelist'].create({
            'name': 'Formula',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'price_discount': 6,
                'price_surcharge': 5,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_one.product_variant_id.id,
            }), (0, 0, {
                # .99 prices
                'compute_price': 'formula',
                'price_surcharge': -0.01,
                'price_round': 1,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_two.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_min_margin': 10,
                'price_max_margin': 100,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_three.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_surcharge': 10,
                'price_max_margin': 5,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_four.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_discount': -100,
                'price_min_margin': 5,
                'price_max_margin': 20,
                'applied_on': '0_product_variant',
                'product_id': self.product_pricelist_five.product_variant_id.id,
            })],
        })
        self.fixed_pricelist_min_quantity = self.env['product.pricelist'].create({
            'name': 'min_quantity ordering',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '0_product_variant',
                'min_quantity': 2,
                'product_id': self.product_pricelist_one.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '0_product_variant',
                'min_quantity': 1,
                'product_id': self.product_pricelist_one.product_variant_id.id,
            })],
        })
        self.pricelist_product_template = self.env['product.pricelist'].create({
            'name': 'Product template',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '1_product',
                'product_tmpl_id': self.product_pricelist_one.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })
        self.pricelist_no_category = self.env['product.pricelist'].create({
            'name': 'Category vs no category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': self.product_category.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })
        self.pricelist_category = self.env['product.pricelist'].create({
            'name': 'Category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '2_product_category',
                'categ_id': self.env.ref('product.product_category_services').id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': self.product_category.id,
            })],
        })

        today = date.today()
        one_week_ago = today - timedelta(weeks=1)
        two_weeks_ago = today - timedelta(weeks=2)
        one_week_from_now = today + timedelta(weeks=1)
        two_weeks_from_now = today + timedelta(weeks=2)
        self.pricelist_date = self.env['product.pricelist'].create({
            'name': 'Dates',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'date_start': two_weeks_ago.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_end': one_week_ago.strftime(DEFAULT_SERVER_DATE_FORMAT),
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'date_start': today.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_end': one_week_from_now.strftime(DEFAULT_SERVER_DATE_FORMAT),
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 3,
                'date_start': one_week_from_now.strftime(DEFAULT_SERVER_DATE_FORMAT),
                'date_end': two_weeks_from_now.strftime(DEFAULT_SERVER_DATE_FORMAT),
            })],
        })
        self.pricelist_cost_base_pricelist = self.env['product.pricelist'].create({
            'name': 'Cost base',
            'item_ids': [(0, 0, {
                'base': 'standard_price',
                'compute_price': 'percentage',
                'percent_price': 55,
            })],
        })
        pricelist_base_pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist base',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': self.pricelist_cost_base_pricelist.id,
                'compute_price': 'percentage',
                'percent_price': 15,
            })],
        })
        self.pricelist_base_2 = self.env['product.pricelist'].create({
            'name': 'Pricelist base 2',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': pricelist_base_pricelist.id,
                'compute_price': 'percentage',
                'percent_price': 3,
            })],
        })
        self.pricelist_base_rounding = self.env['product.pricelist'].create({
            'name': 'Pricelist base rounding',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': self.fixed_pricelist.id,
                'compute_price': 'percentage',
                'percent_price': 0.01,
            })],
        })

        self.all_pricelists = (self.public_pricelist
            + self.fixed_pricelist
            + self.percent_pricelist
            + self.formula_pricelist
            + self.fixed_pricelist_min_quantity
            + self.pricelist_product_template
            + self.pricelist_no_category
            + self.pricelist_category
            + self.pricelist_date
            + self.pricelist_cost_base_pricelist
            + pricelist_base_pricelist
            + self.pricelist_base_2
            + self.pricelist_base_rounding)

        self.all_pricelists.write(dict(currency_id=self.first_company.currency_id.id))

    def setup_test_payment_methods(self):
        self.cash_payment_method = self.env['pos.payment.method'].create({
            'name': 'Cash',
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'journal_id': self.cash_journal.id,
            'company_id': self.env.company.id,
        })
        self.bank_payment_method = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': self.bank_journal.id,
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'company_id': self.env.company.id,
        })
        self.credit_payment_method = self.env['pos.payment.method'].create({
            'name': 'Credit',
            'receivable_account_id': self.company_data['default_account_receivable'].id,
            'split_transactions': True,
            'company_id': self.env.company.id,
        })

    def setup_test_partners(self):
        self.partner_one = self.env['res.partner'].create({
            'name': 'Partner One',
            'email': 'partner.full@example.com',
            'street': '77 Santa Barbara Rd',
            'city': 'Pleasant Hill',
            'state_id': self.env.ref('base.state_us_5').id,
            'zip': '94523',
            'barcode': '0421234567890',
            'country_id': self.env.ref('base.us').id,
        })
        self.partner_two = self.env['res.partner'].create({
            'name': 'Partner Two',
        })
        self.partner_three = self.env['res.partner'].create({
            'name': 'Partner Three',
        })

    def setup_test_taxes(self):
        self.source_tax = self.env['account.tax'].create({'name': "SRC", 'amount': 10})
        self.destination_tax = self.env['account.tax'].create({'name': "DST", 'amount': 5})
        self.tax_10_include = self.env['account.tax'].create({
            'name': 'VAT 10 perc Incl',
            'amount_type': 'percent',
            'amount': 10.0,
            'price_include_override': 'tax_included',
        })
        self.tax_05_include = self.env['account.tax'].create({
            'name': 'VAT 5 perc Incl',
            'amount_type': 'percent',
            'amount': 5.0,
            'price_include_override': 'tax_excluded',
        })
        self.tax_15_include = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 15,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        invoice_rep_lines = (self.tax_10_include | self.tax_05_include).mapped('invoice_repartition_line_ids')
        refund_rep_lines = (self.tax_10_include | self.tax_05_include).mapped('refund_repartition_line_ids')
        (invoice_rep_lines | refund_rep_lines).write({
            'account_id': self.company_data['default_account_tax_sale'].id
        })

    def setup_test_journals(self):
        self.cash_journal = self.env['account.journal'].create({
            'name': 'Cash',
            'type': 'cash',
            'company_id': self.company.id,
            'code': 'CSHO',
            'sequence': 10,
        })
        self.invoice_journal = self.env['account.journal'].create({
            'name': 'Customer Invoice',
            'type': 'sale',
            'company_id': self.company.id,
            'code': 'INVO',
            'sequence': 11,
        })
        self.sale_journal = self.env['account.journal'].create({
            'name':'PoS Sale',
            'type': 'sale',
            'code': 'POSO',
            'company_id': self.company.id,
            'sequence': 12,
        })
        self.bank_journal = self.env['account.journal'].create({
            'name': 'Bank',
            'type': 'bank',
            'company_id': self.company.id,
            'code': 'BNKO',
            'sequence': 13,
        })

    def setup_test_categories(self):
        self.product_category = self.env['product.category'].create({
            'name': 'Services',
            'parent_id': self.env.ref('product.product_category_services').id,
        })
        self.category_things = self.env['pos.category'].create({
            'name': 'Things',
        })
        self.category_items = self.env['pos.category'].create({
            'name': 'Items',
        })
        self.category_articles = self.env['pos.category'].create({
            'name': 'Articles',
        })
        self.category_configurables = self.env['pos.category'].create({
            'name': 'Configurables',
        })
        self.category_pricelist = self.env['pos.category'].create({
            'name': 'Pricelist',
        })

    def setup_test_products(self):
        # Special products
        self.product_tip = self.env.ref('point_of_sale.product_product_tip')
        self.product_tip.write({'active': True})
        self.taxed_product = self.env['product.template'].create({
            'name': 'Taxed Product',
            'available_in_pos': True,
            'list_price': 100,
            'taxes_id': [(6, 0, [self.tax_15_include.id])],
        })

        # One click products
        # replace desk organizer
        self.product_awesome_thing = self.env['product.template'].create({
            'name': 'Awesome Thing',
            'available_in_pos': True,
            'list_price': 5.10,
            'taxes_id': False,
            'weight': 0.01,
            'to_weight': True,
            'pos_categ_ids': [(4, self.category_things.id)],
        })
        self.product_awesome_item = self.env['product.template'].create({
            'name': 'Awesome Item',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_items.id)],
        })
        self.product_awesome_article = self.env['product.template'].create({
            'name': 'Awesome Article',
            'available_in_pos': True,
            'list_price': 2.83,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_articles.id)],
        })
        self.product_quality_thing = self.env['product.template'].create({
            'name': 'Quality Thing',
            'available_in_pos': True,
            'list_price': 1.00,
            'taxes_id': False,
            'barcode': '2305000000004',
            'pos_categ_ids': [(4, self.category_things.id)],
        })
        self.product_quality_item = self.env['product.template'].create({
            'name': 'Quality Item',
            'available_in_pos': True,
            'list_price': 3.19,
            'taxes_id': False,
            'barcode': '0123456789',
            'pos_categ_ids': [(4, self.category_items.id)],
        })
        self.product_quality_article = self.env['product.template'].create({
            'name': 'Quality Article',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'barcode': '2100005000000',
            'pos_categ_ids': [(4, self.category_articles.id)],
        })

        # Product for pricelist testing
        # Old wall_shelf product
        self.product_pricelist_one = self.env['product.template'].create({
            'name': 'Product for pricelist 1',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_pricelist.id)],
        })
        # Old small_shelf product
        self.product_pricelist_two = self.env['product.template'].create({
            'name': 'Product for pricelist 2',
            'available_in_pos': True,
            'list_price': 2.83,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_pricelist.id)],
        })
        # Old magnetic_board product
        self.product_pricelist_three = self.env['product.template'].create({
            'name': 'Product for pricelist 3',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_pricelist.id)],
        })
        # Old monitor_stand product
        self.product_pricelist_four = self.env['product.template'].create({
            'name': 'Product for pricelist 4',
            'available_in_pos': True,
            'list_price': 3.19,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_pricelist.id)],
        })
        # Old desk_pad product
        self.product_pricelist_five = self.env['product.template'].create({
            'name': 'Product for pricelist 5',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_pricelist.id)],
        })
        # Old letter_tray product
        self.product_pricelist_six = self.env['product.template'].create({
            'name': 'Product for pricelist 6',
            'available_in_pos': True,
            'list_price': 4.80,
            'categ_id': self.env.ref('product.product_category_services').id,
            'taxes_id': [(6, 0, [self.source_tax.id])],
            'pos_categ_ids': [(4, self.category_pricelist.id)],
        })

        # Configurable products
        self.product_configurable = self.env['product.template'].create({
            'name': 'Configurable 1',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_configurables.id)],
        })
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
            'create_variant': 'always',
        })
        color_attribute_red = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': color_attribute.id,
            'html_color': '#ff0000',
        })
        color_attribute_blue = self.env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': color_attribute.id,
            'html_color': '#0000ff',
        })
        color_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_configurable.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, [color_attribute_red.id, color_attribute_blue.id])]
        })
        color_attribute_line.product_template_value_ids[0].price_extra = 1
        select_attribute = self.env['product.attribute'].create({
            'name': 'Select',
            'display_type': 'select',
            'create_variant': 'no_variant',
        })
        select_attribute_one = self.env['product.attribute.value'].create({
            'name': 'One',
            'attribute_id': select_attribute.id,
        })
        select_attribute_two = self.env['product.attribute.value'].create({
            'name': 'Two',
            'attribute_id': select_attribute.id,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_configurable.id,
            'attribute_id': select_attribute.id,
            'value_ids': [(6, 0, [select_attribute_one.id, select_attribute_two.id])]
        })
        radio_attribute = self.env['product.attribute'].create({
            'name': 'Radio',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })
        radio_attribute_one = self.env['product.attribute.value'].create({
            'name': 'One',
            'attribute_id': radio_attribute.id,
        })
        radio_attribute_two = self.env['product.attribute.value'].create({
            'name': 'Two',
            'attribute_id': radio_attribute.id,
        })
        radio_attribute_custom = self.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': radio_attribute.id,
            'is_custom': True,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_configurable.id,
            'attribute_id': radio_attribute.id,
            'value_ids': [(6, 0, [radio_attribute_one.id, radio_attribute_two.id, radio_attribute_custom.id])]
        })
        color_attribute_line.product_template_value_ids[1].is_custom = True
        self.product_configurable_multi = self.env['product.template'].create({
            'name': 'Configurable Multi',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.category_configurables.id)],
        })
        multi_attributes = self.env['product.attribute'].create({
            'name': 'Multi',
            'display_type': 'multi',
            'create_variant': 'no_variant',
        })
        multi_attributes_1 = self.env['product.attribute.value'].create({
            'name': 'Multi 1',
            'attribute_id': multi_attributes.id,
        })
        multi_attributes_2 = self.env['product.attribute.value'].create({
            'name': 'Multi 2',
            'attribute_id': multi_attributes.id,
        })
        multi_attributes_3 = self.env['product.attribute.value'].create({
            'name': 'Multi 3',
            'attribute_id': multi_attributes.id,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_configurable_multi.id,
            'attribute_id': multi_attributes.id,
            'value_ids': [(6, 0, [multi_attributes_1.id, multi_attributes_2.id, multi_attributes_3.id])]
        })
