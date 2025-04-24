
from datetime import date, timedelta

from odoo.fields import Command
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


def archive_products(env):
    # Archive all existing product to avoid noise during the tours
    all_pos_product = env['product.template'].search([('available_in_pos', '=', True)])
    tip = env.ref('point_of_sale.product_product_tip').product_tmpl_id
    (all_pos_product - tip)._write({'active': False})


def setup_test_pos_users(self):
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


def setup_test_pos_partners(self):
    # Set customers
    self.partner_full = self.env['res.partner'].create({
        'name': 'Partner Full',
        'email': 'partner.full@example.com',
        'phone': '9898989899',
        'street': '77 Santa Barbara Rd',
        'city': 'Pleasant Hill',
        'state_id': self.env.ref('base.state_us_5').id,  # California
        'zip': '94523',
        'country_id': self.env.ref('base.us').id,
    })
    self.partner1 = self.env['res.partner'].create({'name': 'Partner Test 1'})
    self.partner_test_2 = self.env['res.partner'].create({'name': 'Partner Test 2'})
    self.partner_test_3 = self.env['res.partner'].create({'name': 'Partner Test 3'})
    self.env['res.partner'].create({
        'name': 'Deco Addict',
    })

    res_partner_18 = self.env['res.partner'].create({
        'name': 'Lumber Inc',
        'is_company': True,
    })
    res_partner_18.property_product_pricelist = self.excluded_pricelist


def setup_test_pos_journals(self):
    journal_obj = self.env['account.journal']

    self.bank_journal = journal_obj.create({
        'name': 'Bank Test',
        'type': 'bank',
        'company_id': self.env.company.id,
        'code': 'BNK',
        'sequence': 10,
    })
    self.cash_journal = journal_obj.create({
        'name': 'Cash Test',
        'type': 'cash',
        'company_id': self.env.company.id,
        'code': 'CSH',
        'sequence': 10,
    })
    self.sale_journal = journal_obj.create({
        'name': 'Sales Journal - Test',
        'code': 'TSJ',
        'type': 'sale',
        'company_id': self.env.company.id
    })


def setup_test_pos_payment_mehods(self):
    pm_obj = self.env['pos.payment.method']

    self.bank_payment_method = pm_obj.create({
        'name': 'Bank',
        'journal_id': self.bank_journal.id,
        'is_cash_count': False,
        'split_transactions': False,
        'company_id': self.env.company.id,
    })
    self.cash_payment_method = pm_obj.create({
        'name': 'Cash',
        'journal_id': self.cash_journal.id,
        'receivable_account_id': self.account_receivable.id,
        'company_id': self.env.company.id,
    })
    self.split_bank_payment_method = pm_obj.create({
        'name': 'Bank / Split',
        'split_transactions': True,
        'company_id': self.env.company.id,
    })
    self.customer_account_payment_method = pm_obj.create({
        'name': 'Customer Account',
        'receivable_account_id': self.account_receivable.id,
        'split_transactions': True,
        'company_id': self.env.company.id,
    })


def setup_test_taxes(self):
    tax_obj = self.env['account.tax']
    self.src_tax = tax_obj.create({'name': "SRC", 'amount': 10})
    self.dst_tax = tax_obj.create({'name': "DST", 'amount': 5})
    self.tax10 = tax_obj.create({
        "name": "Tax 10% excl",
        "amount": 10,
        "amount_type": "percent",
        "type_tax_use": "sale",
    })
    self.tax20in = tax_obj.create({
        "name": "20% incl",
        "amount": 20,
        "amount_type": "percent",
        "type_tax_use": "sale",
        "price_include_override": "tax_included",
        "include_base_amount": True,
    })
    self.tax30 = tax_obj.create({
        "name": "30%",
        "amount": 30,
        "amount_type": "percent",
        "type_tax_use": "sale",
    })

    self.account_tax_10_incl = tax_obj.create({
        'name': 'VAT 10 perc Incl',
        'amount_type': 'percent',
        'amount': 10.0,
        'price_include_override': 'tax_included',
    })
    # account_tax_05_incl
    self.account_tax_05_excl = tax_obj.create({
        'name': 'VAT 5 perc Incl',
        'amount_type': 'percent',
        'amount': 5.0,
        'price_include_override': 'tax_excluded',
    })
    # create a second VAT tax of 5% but this time for a child company, to
    # ensure that only product taxes of the current session's company are considered
    # (this tax should be ignore when computing order's taxes in following tests)
    # account_tax_05_incl_chicago
    self.account_tax_05_excl_chicago = tax_obj.create({
        'name': 'VAT 05 perc Excl (US)',
        'amount_type': 'percent',
        'amount': 5.0,
        'price_include_override': 'tax_excluded',
        'company_id': self.company_data_2['company'].id,
    })

    # Set account_id in the generated repartition lines. Automatically, nothing is set.
    invoice_rep_lines = (self.account_tax_05_excl | self.account_tax_10_incl).mapped('invoice_repartition_line_ids')
    refund_rep_lines = (self.account_tax_05_excl | self.account_tax_10_incl).mapped('refund_repartition_line_ids')
    # Expense account, should just be something else than receivable/payable
    (invoice_rep_lines | refund_rep_lines).write({'account_id': self.company_data['default_account_tax_sale'].id})


def setup_test_pos_pricelists(self):
    pricelist_obj = self.env['product.pricelist']

    self.fixed_pricelist = pricelist_obj.create({
        'name': 'Fixed',
        'item_ids': [(0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 1,
        }), (0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 2,
            'applied_on': '0_product_variant',
            'product_id': self.wall_shelf.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 13.95,  # test for issues like in 7f260ab517ebde634fc274e928eb062463f0d88f
            'applied_on': '0_product_variant',
            'product_id': self.small_shelf.product_variant_id.id,
        })],
    })
    self.percentage_pricelist = pricelist_obj.create({
        'name': 'Percentage',
        'item_ids': [(0, 0, {
            'compute_price': 'percentage',
            'percent_price': 100,
            'applied_on': '0_product_variant',
            'product_id': self.wall_shelf.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'percentage',
            'percent_price': 99,
            'applied_on': '0_product_variant',
            'product_id': self.small_shelf.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'percentage',
            'percent_price': 0,
            'applied_on': '0_product_variant',
            'product_id': self.magnetic_board.product_variant_id.id,
        })],
    })
    self.formula_pricelist = pricelist_obj.create({
        'name': 'Formula',
        'item_ids': [(0, 0, {
            'compute_price': 'formula',
            'price_discount': 6,
            'price_surcharge': 5,
            'applied_on': '0_product_variant',
            'product_id': self.wall_shelf.product_variant_id.id,
        }), (0, 0, {
            # .99 prices
            'compute_price': 'formula',
            'price_surcharge': -0.01,
            'price_round': 1,
            'applied_on': '0_product_variant',
            'product_id': self.small_shelf.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'formula',
            'price_min_margin': 10,
            'price_max_margin': 100,
            'applied_on': '0_product_variant',
            'product_id': self.magnetic_board.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'formula',
            'price_surcharge': 10,
            'price_max_margin': 5,
            'applied_on': '0_product_variant',
            'product_id': self.monitor_stand.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'formula',
            'price_discount': -100,
            'price_min_margin': 5,
            'price_max_margin': 20,
            'applied_on': '0_product_variant',
            'product_id': self.desk_pad.product_variant_id.id,
        })],
    })
    self.fixed_min_quantity_pricelist = pricelist_obj.create({
        'name': 'min_quantity ordering',
        'item_ids': [(0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 1,
            'applied_on': '0_product_variant',
            'min_quantity': 2,
            'product_id': self.wall_shelf.product_variant_id.id,
        }), (0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 2,
            'applied_on': '0_product_variant',
            'min_quantity': 1,
            'product_id': self.wall_shelf.product_variant_id.id,
        })],
    })
    self.product_template_pricelist = pricelist_obj.create({
        'name': 'Product template',
        'item_ids': [(0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 1,
            'applied_on': '1_product',
            'product_tmpl_id': self.wall_shelf.id,
        }), (0, 0, {
            'compute_price': 'fixed',
            'fixed_price': 2,
        })],
    })
    self.no_category_pricelist = pricelist_obj.create({
        # no category has precedence over category
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
    self.category_pricelist = pricelist_obj.create({
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

    self.public_pricelist = pricelist_obj.create({
        'name': 'Public Pricelist',
    })
    self.date_pricelists = pricelist_obj.create({
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
    self.cost_base_pricelist = pricelist_obj.create({
        'name': 'Cost base',
        'item_ids': [(0, 0, {
            'base': 'standard_price',
            'compute_price': 'percentage',
            'percent_price': 55,
        })],
    })
    self.pricelist_base_pricelist = pricelist_obj.create({
        'name': 'Pricelist base',
        'item_ids': [(0, 0, {
            'base': 'pricelist',
            'base_pricelist_id': self.cost_base_pricelist.id,
            'compute_price': 'percentage',
            'percent_price': 15,
        })],
    })
    self.pricelist_base2_pricelist = pricelist_obj.create({
        'name': 'Pricelist base 2',
        'item_ids': [(0, 0, {
            'base': 'pricelist',
            'base_pricelist_id': self.pricelist_base_pricelist.id,
            'compute_price': 'percentage',
            'percent_price': 3,
        })],
    })
    self.base_rounding_pricelist = pricelist_obj.create({
        'name': 'Pricelist base rounding',
        'item_ids': [(0, 0, {
            'base': 'pricelist',
            'base_pricelist_id': self.fixed_pricelist.id,
            'compute_price': 'percentage',
            'percent_price': 0.01,
        })],
    })

    self.excluded_pricelist = pricelist_obj.create({
        'name': 'Not loaded'
    })

    self.all_pricelists = pricelist_obj.search([
        ('id', '!=', self.excluded_pricelist.id),
        '|', ('company_id', '=', self.main_company.id), ('company_id', '=', False)
    ])
    self.all_pricelists.write(dict(currency_id=self.main_company.currency_id.id))


def setup_test_pos_configs(self):
    self.env['pos.config'].search([]).unlink()
    self.main_pos_config = self.env['pos.config'].create({
        'name': 'Shop',
        'module_pos_restaurant': False,
        'tax_regime_selection': True,
        'fiscal_position_ids': [(0, 0, {
                                        'name': "FP-POS-2M",
                                        'tax_ids': [
                                            (0, 0, {'tax_src_id': self.src_tax.id,
                                                    'tax_dest_id': self.src_tax.id}),
                                            (0, 0, {'tax_src_id': self.src_tax.id,
                                                    'tax_dest_id': self.dst_tax.id})]
                                        })],
        'journal_id': self.sale_journal.id,
        'invoice_journal_id': self.sale_journal.id,
        'payment_method_ids': [
            (6, 0, [
                self.cash_payment_method.id,
                self.bank_payment_method.id,
                self.customer_account_payment_method.id,
            ]),
        ],
        'use_pricelist': True,
        'pricelist_id': self.public_pricelist.id,
        'available_pricelist_ids': [(4, pricelist.id) for pricelist in self.all_pricelists],
        'iface_tipproduct': True,
        'tip_product_id': self.tip_product.id,
        'ship_later': True,
    })
    self.pos_config = self.main_pos_config


def setup_test_pos_categories(self):
    self.product_category = self.env['product.category'].create({
        'name': 'Services',
        'parent_id': self.env.ref('product.product_category_services').id,
    })

    pos_catg_obj = self.env['pos.category']

    self.pos_desk_misc_test = pos_catg_obj.create({
        'name': 'Misc test',
    })
    self.pos_cat_chair_test = pos_catg_obj.create({
        'name': 'Chair test',
    })
    self.pos_cat_desk_test = pos_catg_obj.create({
        'name': 'Desk test',
    })


def setup_test_product_attribute(self):
    # no_variant color
    self.color_attribute = self.env['product.attribute'].create({
        'name': 'Color',
        'display_type': 'color',
        'create_variant': 'no_variant',
        'value_ids': [
            (0, 0, {'name': 'Red', 'html_color': '#ff0000'}),
            (0, 0, {'name': 'Blue', 'html_color': '#0000ff'}),
        ]
    })

    # no_variant selection
    self.chair_legs_attribute = self.env['product.attribute'].create({
        'name': 'Chair Legs',
        'display_type': 'select',
        'create_variant': 'no_variant',
        'value_ids': [
            (0, 0, {'name': 'Metal'}),
            (0, 0, {'name': 'Wood'}),
        ]
    })

    # no_variant radio with custom attribute
    self.fabrics_attribute = self.env['product.attribute'].create({
        'name': 'Fabrics',
        'display_type': 'radio',
        'create_variant': 'no_variant',
        'value_ids': [
            (0, 0, {'name': 'Leather'}),
            (0, 0, {'name': 'Wool'}),
            (0, 0, {'name': 'Other', 'is_custom': True}),
        ]
    })

    # always variant color
    self.always_color_attribute = self.env['product.attribute'].create({
        'name': 'Always Color',
        'display_type': 'color',
        'create_variant': 'always',
        'value_ids': [
            (0, 0, {'name': 'Black', 'html_color': '#000000'}),
            (0, 0, {'name': 'White', 'html_color': '#ffffff'}),
        ]
    })


def setup_test_pos_products(self):
    archive_products(self.env)
    self.tip_product = self.env.ref('point_of_sale.product_product_tip')
    self.tip_product.write({
        'taxes_id': False
    })

    product_teml_obj = self.env['product.template']
    product_obj = self.env['product.product']

    # test an extra price on an attribute
    self.whiteboard_pen = product_teml_obj.create({
        'name': 'Whiteboard Pen',
        'available_in_pos': True,
        'list_price': 1.20,
        'taxes_id': False,
        'weight': 0.01,
        'to_weight': True,
        'pos_categ_ids': [(4, self.pos_desk_misc_test.id)],
    })
    attribute = self.env['product.attribute'].create({
        'name': 'add 2',
        'value_ids': [(0, 0, {'name': 'add 2'})]
    })
    whiteboard_pen_attr_line = self.env['product.template.attribute.line'].create({
        'product_tmpl_id': self.whiteboard_pen.id,
        'attribute_id': attribute.id,
        'value_ids': [(6, 0, attribute.value_ids.ids)]
    })
    whiteboard_pen_attr_line.product_template_value_ids[0].price_extra = 2

    # Pricelist Products
    self.wall_shelf = product_teml_obj.create({
        'name': 'Wall Shelf Unit',
        'available_in_pos': True,
        'list_price': 1.98,
        'taxes_id': False,
        'barcode': '2100005000000',
    })
    self.small_shelf = product_teml_obj.create({
        'name': 'Small Shelf',
        'available_in_pos': True,
        'list_price': 2.83,
        'taxes_id': False,
    })
    self.magnetic_board = product_teml_obj.create({
        'name': 'Magnetic Board',
        'available_in_pos': True,
        'list_price': 1.98,
        'taxes_id': False,
        'barcode': '2305000000004',
    })
    self.monitor_stand = product_teml_obj.create({
        'name': 'Monitor Stand',
        'available_in_pos': True,
        'list_price': 3.19,
        'taxes_id': False,
        'barcode': '0123456789',  # No pattern in barcode nomenclature
    })
    self.desk_pad = product_teml_obj.create({
        'name': 'Desk Pad',
        'available_in_pos': True,
        'list_price': 1.98,
        'taxes_id': False,
        'pos_categ_ids': [(4, self.pos_cat_desk_test.id)],
    })

    # Taxed Products
    self.letter_tray = product_teml_obj.create({
        'name': 'Letter Tray',
        'available_in_pos': True,
        'list_price': 4.80,
        'taxes_id': [(6, 0, [self.src_tax.id])],
        'categ_id': self.env.ref('product.product_category_services').id,
        'pos_categ_ids': [(4, self.pos_cat_chair_test.id)],
    })

    self.desk_organizer = product_teml_obj.create({
        'name': 'Desk Organizer',
        'available_in_pos': True,
        'list_price': 5.10,
        'taxes_id': False,
        'barcode': '2300002000007',
    })

    # Configurable Products
    self.configurable_chair = product_teml_obj.create({
        'name': 'Configurable Chair',
        'available_in_pos': True,
        'list_price': 30,
        'taxes_id': False,
    })

    chair_color_line = self.env['product.template.attribute.line'].create({
        'product_tmpl_id': self.configurable_chair.id,
        'attribute_id': self.color_attribute.id,
        'value_ids': [(6, 0, self.color_attribute.value_ids.ids)]
    })
    chair_color_line.product_template_value_ids[0].price_extra = 1

    self.env['product.template.attribute.line'].create({
        'product_tmpl_id': self.configurable_chair.id,
        'attribute_id': self.chair_legs_attribute.id,
        'value_ids': [(6, 0, self.chair_legs_attribute.value_ids.ids)]
    })

    self.env['product.template.attribute.line'].create({
        'product_tmpl_id': self.configurable_chair.id,
        'attribute_id': self.fabrics_attribute.id,
        'value_ids': [(6, 0, self.fabrics_attribute.value_ids.ids)]
    })
    chair_color_line.product_template_value_ids[1].is_custom = True

    # product.product
    self.test_product3 = product_obj.create({
        'name': 'Test Product 3',
        'list_price': 450,
        'taxes_id': [(6, 0, [self.account_tax_10_incl.id])],
        'available_in_pos': True,
    })
    self.test_product4 = product_obj.create({
        'name': 'Test Product 4',
        'list_price': 750,
        'company_id': False,
        'taxes_id': [(6, 0, [self.account_tax_05_excl.id, self.account_tax_05_excl_chicago.id])],
        'available_in_pos': True,
    })

    # tracked products
    self.serial_product = product_obj.create({
        'name': 'Serial Product',
        'is_storable': True,
        'tracking': 'serial',
        'list_price': 10.0,
        'taxes_id': False,
    })
    self.lot_product = product_obj.create({
        'name': 'Lot Product',
        'is_storable': True,
        'tracking': 'lot',
        'list_price': 10.0,
        'taxes_id': False,
    })


def setup_test_product_combo_items(self):
    combo_product_1 = self.env["product.product"].create({
        "name": "Combo Product 1",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 10,
        "taxes_id": [(6, 0, [self.tax10.id])],
        "pos_categ_ids": [(6, 0, [self.pos_desk_misc_test.id])],
    })

    combo_product_2 = self.env["product.product"].create({
        "name": "Combo Product 2",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 11,
        "taxes_id": [(6, 0, [self.tax20in.id])],
        "pos_categ_ids": [(6, 0, [self.pos_desk_misc_test.id])],
    })

    combo_product_3 = self.env["product.product"].create({
        "name": "Combo Product 3",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 16,
        "taxes_id": [(6, 0, [self.tax30.id])],
        "pos_categ_ids": [(6, 0, [self.pos_desk_misc_test.id])],
    })

    self.desk_accessories_combo = self.env["product.combo"].create({
        "name": "Desk Accessories Combo",
        "combo_item_ids": [
            Command.create({
                "product_id": combo_product_1.id,
                "extra_price": 0,
            }),
            Command.create({
                "product_id": combo_product_2.id,
                "extra_price": 0,
            }),
            Command.create({
                "product_id": combo_product_3.id,
                "extra_price": 2,
            }),
        ],
    })

    combo_product_4 = self.env["product.product"].create({
        "name": "Combo Product 4",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 20,
        "taxes_id": [(6, 0, [self.tax10.id])],
        "pos_categ_ids": [(6, 0, [self.pos_cat_chair_test.id])],
    })

    combo_product_5 = self.env["product.product"].create({
        "name": "Combo Product 5",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 25,
        "taxes_id": [(6, 0, [self.tax20in.id])],
        "pos_categ_ids": [(6, 0, [self.pos_cat_chair_test.id])],
    })

    self.desks_combo = self.env["product.combo"].create({
        "name": "Desks Combo",
        "combo_item_ids": [
            Command.create({
                "product_id": combo_product_4.id,
                "extra_price": 0,
            }),
            Command.create({
                "product_id": combo_product_5.id,
                "extra_price": 2,
            }),
        ],
    })

    combo_product_6 = self.env["product.product"].create({
        "name": "Combo Product 6",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 30,
        "taxes_id": [(6, 0, [self.tax30.id])],
        "pos_categ_ids": [(6, 0, [self.pos_cat_desk_test.id])],
    })

    combo_product_7 = self.env["product.product"].create({
        "name": "Combo Product 7",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 32,
        "taxes_id": [(6, 0, [self.tax10.id])],
        "pos_categ_ids": [(6, 0, [self.pos_cat_desk_test.id])],
    })

    combo_product_8 = self.env["product.product"].create({
        "name": "Combo Product 8",
        "is_storable": True,
        "available_in_pos": True,
        "list_price": 40,
        "taxes_id": [(6, 0, [self.tax20in.id])],
        "pos_categ_ids": [(6, 0, [self.pos_cat_desk_test.id])],
    })

    self.chairs_combo = self.env["product.combo"].create({
        "name": "Chairs Combo",
        "combo_item_ids": [
            Command.create({
                "product_id": combo_product_6.id,
                "extra_price": 0,
            }),
            Command.create({
                "product_id": combo_product_7.id,
                "extra_price": 0,
            }),
            Command.create({
                "product_id": combo_product_8.id,
                "extra_price": 5,
            }),
        ],
    })

    # Create Office Combo
    self.office_combo = self.env["product.product"].create({
        "available_in_pos": True,
        "list_price": 40,
        "name": "Office Combo",
        "type": "combo",
        "uom_id": self.env.ref("uom.product_uom_unit").id,
        "combo_ids": [
            (6, 0, [self.desks_combo.id, self.chairs_combo.id, self.desk_accessories_combo.id])
        ],
        "pos_categ_ids": [(6, 0, [self.pos_cat_chair_test.id])],
    })


def setup_test_pos(cls):
    cls.env.user.group_ids += cls.env.ref('point_of_sale.group_pos_manager')

    cls.account_receivable = cls.env['account.account'].create({
        'code': 'X1012',
        'name': 'Account Receivable - Test',
        'account_type': 'asset_receivable',
        'reconcile': True
    })
    cls.env.company.account_default_pos_receivable_account_id = cls.account_receivable

    cls.env['ir.default'].set('res.partner', 'property_account_receivable_id', cls.company_data['default_account_receivable'].id, company_id=cls.main_company.id)
    # Pricelists are set below, do not take demo data into account
    cls.env['res.partner'].sudo().invalidate_model(['property_product_pricelist', 'specific_property_product_pricelist'])
    # remove the all specific values for all companies only for test
    cls.env.cr.execute('UPDATE res_partner SET specific_property_product_pricelist = NULL')
    cls.company_data['default_journal_cash'].pos_payment_method_ids.unlink()

    setup_test_pos_users(cls)
    setup_test_pos_journals(cls)
    setup_test_pos_payment_mehods(cls)
    setup_test_taxes(cls)
    setup_test_pos_categories(cls)
    setup_test_product_attribute(cls)
    setup_test_pos_products(cls)
    setup_test_product_combo_items(cls)
    setup_test_pos_pricelists(cls)
    setup_test_pos_partners(cls)
    setup_test_pos_configs(cls)

    # Change the default sale pricelist of customers,
    # so the js tests can expect deterministically this pricelist when selecting a customer.
    # bad hack only for test
    cls.env['ir.default'].set("res.partner", "specific_property_product_pricelist", cls.public_pricelist.id, company_id=cls.main_company.id)
