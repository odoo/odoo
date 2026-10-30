# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo import Command
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class PosTestRecords(AccountTestInvoicingCommon):
    """Shared record factories for backend and HTTP POS tests."""

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def _create_company(cls, company_xmlid=None, **create_values):
        # Avoid the branch fixture, which may contain demo journal entries.
        create_values.setdefault('candidate_xmlids', (
            'base.test_company', 'base.test_company_template', 'base.test_company_template2',
        ))
        return super()._create_company(company_xmlid=company_xmlid, **create_values)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls._archive_products()
        cls.env.user.group_ids |= cls.env.ref('point_of_sale.group_pos_manager')

        # Currencies - USD, EUR
        cls.company_currency = cls.company.currency_id
        cls.other_currency = cls.setup_other_currency('EUR', rates=[('2000-01-01', 0.5)], rounding=0.001)
        cls.pos_receivable_account = cls.company.account_default_pos_receivable_account_id

        if 'enforce_cities' in cls.env['res.country']._fields:
            cls.company.country_id.enforce_cities = False

        cls.env['ir.default'].set(
            'res.partner', 'property_account_receivable_id',
            cls.pos_receivable_account.id, company_id=cls.company.id,
        )
        # Pricelists are set below, do not take demo data into account.
        cls.env['res.partner'].sudo().invalidate_model(['property_product_pricelist', 'specific_property_product_pricelist'])
        # Remove specific pricelists for all companies in the test transaction.
        cls.env.cr.execute('UPDATE res_partner SET specific_property_product_pricelist = NULL')

        cls._setup_account_journals()
        cls._setup_payment_methods()
        cls._setup_categories()
        cls._setup_taxes()

        cls._setup_pos_products()
        cls._setup_pricelists()
        cls._setup_customers()
        cls._setup_fiscal_positions()
        cls._setup_pos_configs()

        cls._setup_attribute_products()
        cls.env['ir.default'].set('res.partner', 'specific_property_product_pricelist', cls.public_pricelist.id, company_id=cls.company.id)

        # TODO-PARP:
        # cls._setup_combo_product()  # will replace setup_product_combo_items

    @classmethod
    def _archive_products(cls):
        # Archive all existing product.
        cls.env['product.template'].search([('available_in_pos', '=', True)])._write({'active': False})

    @classmethod
    def create_product_template(cls, name, list_price, pos_categ_ids=[], tax_ids=[], **kwargs):
        return cls.env['product.template'].create({
            'is_storable': True,
            'available_in_pos': True,
            'name': name,
            'list_price': list_price,
            'taxes_id': [Command.set(list(tax_ids))],
            'pos_categ_ids': [Command.set(list(pos_categ_ids))],
            **kwargs,
        })

    @classmethod
    def create_product(cls, name, lst_price, tax_ids=[], **kwargs):
        return cls.env['product.product'].create({
            'is_storable': True,
            'available_in_pos': True,
            'taxes_id': [Command.set(list(tax_ids))],
            'name': name,
            'lst_price': lst_price,
            'company_id': cls.env.company.id,
            **kwargs,
        })

    @classmethod
    def _setup_users(cls):
        cls.pos_user = cls.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_user',
            'password': 'pos_user',
            'group_ids': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
                (4, cls.env.ref('base.group_partner_manager').id),
            ],
            'tz': 'America/New_York',
        })
        cls.pos_admin = cls.env['res.users'].create({
            'name': 'A powerful PoS man!',
            'login': 'pos_admin',
            'password': 'pos_admin',
            'group_ids': [
                (4, cls.env.ref('point_of_sale.group_pos_manager').id),
            ],
            'tz': 'America/New_York',
        })

        cls.pos_user.partner_id.email = 'pos_user@test.com'
        cls.pos_admin.partner_id.email = 'pos_admin@test.com'

    @classmethod
    def _setup_categories(cls):
        # PoS Categories
        (cls.pos_desk_misc_test, cls.pos_cat_chair_test, cls.pos_cat_desk_test,
         cls.pos_car_other_test) = cls.env['pos.category'].create([
            {'name': 'Misc test', 'sequence': 0},
            {'name': 'Chair test', 'sequence': 1},
            {'name': 'Desk test', 'sequence': 2},
            {'name': 'Tax fifteen incl', 'sequence': 3},
        ])
        # Product Categories
        cls.categ_basic = cls.env.ref('product.product_category_services')
        cls.categ_services = cls.env['product.category'].create({
            'name': 'Services',
            'parent_id': cls.categ_basic.id,
        })

    @classmethod
    def _setup_pos_products(cls):
        cls.whiteboard_pen = cls.create_product_template('Whiteboard Pen', 10, [cls.pos_desk_misc_test.id], weight=0.01)
        cls.wall_shelf = cls.create_product_template('Wall Shelf Unit', 20, barcode='2100005000000')
        cls.small_shelf = cls.create_product_template('Small Shelf', 10, tax_ids=[cls.taxes['tax5_incl'].id])
        cls.magnetic_board = cls.create_product_template('Magnetic Board', 20, tax_ids=[cls.taxes['tax5_incl'].id], barcode='2305000000004')
        cls.monitor_stand = cls.create_product_template('Monitor Stand', 10, tax_ids=[cls.taxes['tax10_incl'].id], barcode='0123456789')
        cls.desk_pad = cls.create_product_template('Desk Pad', 20, [cls.pos_cat_desk_test.id], [cls.taxes['tax10_incl'].id])
        cls.letter_tray = cls.create_product_template(
            'Letter Tray',
            10,
            pos_categ_ids=[cls.pos_cat_chair_test.id],
            tax_ids=[cls.taxes['tax15_incl'].id],
            categ_id=cls.categ_basic.id,
        )
        cls.desk_organizer = cls.create_product_template('Desk Organizer', 20, tax_ids=[cls.taxes['tax15_incl'].id], barcode='2300002000007')

        cls.configurable_chair = cls.create_product_template('Configurable Chair', 10.0)
        cls.vanela_gathiya = cls.create_product_template('Vanela Gathiya', 10.0, to_weight=True)

        cls.ten_dollars_no_tax = cls.whiteboard_pen
        cls.twenty_dollars_no_tax = cls.wall_shelf
        cls.ten_dollars_with_5_incl = cls.small_shelf
        cls.twenty_dollars_with_5_incl = cls.magnetic_board
        cls.ten_dollars_with_10_incl = cls.monitor_stand
        cls.twenty_dollars_with_10_incl = cls.desk_pad
        cls.ten_dollars_with_15_incl = cls.letter_tray
        cls.twenty_dollars_with_15_incl = cls.desk_organizer

    @classmethod
    def _setup_customers(cls):
        (
            cls.partner_test_1, cls.partner_test_2, cls.partner_test_3,
            cls.acme_partner, cls.partner_full, cls.excluded_pricelist_partner,
        ) = cls.env['res.partner'].create([
            {'name': 'Partner Test 1'},
            {'name': 'Partner Test 2'},
            {'name': 'Partner Test 3'},
            {'name': 'Acme Corporation'},
            {
                'name': 'APartner Full',
                'email': 'partner.full@example.com',
                'street': '77 Santa Barbara Rd',
                'city': 'Pleasant Hill',
                'state_id': cls.env.ref('base.state_us_5').id,
                'zip': '94523',
                'country_id': cls.env.ref('base.us').id,
            },
            {
                'name': 'Lumber Inc',
                'property_product_pricelist': cls.excluded_pricelist.id,
            },
        ])
        cls.customer = cls.env['res.partner'].create({
            'name': 'Customer 1',
            'property_account_receivable_id': cls.copy_account(cls.receivable_account, {'name': 'Customer 1 Receivable'}).id
        })
        cls.other_customer = cls.env['res.partner'].create({
            'name': 'Other Customer',
            'property_account_receivable_id': cls.env['account.account'].create({
                'name': 'Other Receivable',
                'code': 'RCV00',
                'account_type': 'asset_receivable',
                'internal_group': 'asset',
            }).id,
        })
        # Keep the legacy partner aliases used by backend tests.
        cls.partner_mobt = cls.partner_test_1
        cls.partner_adgu = cls.partner_test_2
        cls.partner_lowe = cls.partner_test_3
        cls.partner_jcb = cls.partner_full
        cls.partner_moda = cls.acme_partner
        cls.partner_stva = cls.excluded_pricelist_partner
        cls.partner_manv, cls.partner_vlst, cls.partner_parp = cls.env['res.partner'].create([
            {'name': 'MANV'}, {'name': 'VLST'}, {'name': 'PARP'},
        ])

        # Unlink some data partners that makes the test crash
        for xmlid in [
            "l10n_us_hr_payroll.res_partner_taxation_va",
            "l10n_us_hr_payroll.res_partner_revenue_dc",
            "l10n_us_hr_payroll.res_partner_pfl_dc",
            "l10n_us_hr_payroll.res_partner_revenue_or",
            "l10n_us_hr_payroll.res_partner_dcbs_or",
            "l10n_us_hr_payroll.res_partner_employment_or",
            "l10n_us_hr_payroll.res_partner_revenue_nc",
            "l10n_us_hr_payroll.res_partner_state_tax_commission_id",
            "l10n_us_hr_payroll.res_partner_department_taxes_vt",
            "l10n_us_hr_payroll.res_partner_department_revenue_il",
            "l10n_us_hr_payroll.res_partner_department_revenue_az",
        ]:
            if partner := cls.env.ref(xmlid, raise_if_not_found=False):
                partner.unlink()

    @classmethod
    def _setup_taxes(cls):
        def create_tax(percentage, price_include_override='tax_excluded'):
            return cls.env['account.tax'].create({
                'name': f"Tax {percentage}% {'incl' if price_include_override == 'tax_excluded' else 'excl'}",
                'amount': percentage,
                'price_include_override': price_include_override,
            })
        cls.taxes = {
            'tax7': create_tax(7),
            'tax10': create_tax(10),
            'tax5_incl': create_tax(5, 'tax_included'),
            'tax10_incl': create_tax(10, 'tax_included'),
            'tax15_incl': create_tax(15, 'tax_included'),
            'tax21_incl': create_tax(21, 'tax_included'),
        }
        cls.taxes['tax_group_7_10'] = cls.env['account.tax'].create({
            'name': 'Tax 7+10 %',
            'amount_type': 'group',
            'children_tax_ids': [Command.set((cls.taxes['tax7'] + cls.taxes['tax10']).ids)]
        })

    @classmethod
    def _setup_account_journals(cls):
        cls.receivable_account = cls.company_data['default_account_receivable']

        cls.pos_receivable_cash = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Cash'})
        cls.pos_receivable_bank = cls.copy_account(cls.company.account_default_pos_receivable_account_id, {'name': 'POS Receivable Bank'})
        cls.outstanding_bank = cls.copy_account(cls.inbound_payment_method_line.payment_account_id, {'name': 'Outstanding Bank'})

        cls.other_cash_journal = cls.env['account.journal'].create({
            'name': 'Cash Other',
            'type': 'cash',
            'company_id': cls.company.id,
            'code': 'CSHO',
            'sequence': 10,
            'currency_id': cls.other_currency.id,
        })
        cls.other_sales_journal = cls.env['account.journal'].create({
            'name': 'PoS Sale Other',
            'type': 'sale',
            'code': 'POSO',
            'company_id': cls.company.id,
            'sequence': 12,
            'currency_id': cls.other_currency.id,
        })
        cls.other_bank_journal = cls.env['account.journal'].create({
            'name': 'Bank Other',
            'type': 'bank',
            'company_id': cls.company.id,
            'code': 'BNKO',
            'sequence': 13,
            # TODO-PARP: Keep bank methods compatible with legacy tests selecting across configs.
            'currency_id': False,
        })
        cls.bank_journal = cls.company_data['default_journal_bank']

    @classmethod
    def _setup_payment_methods(cls):
        # drop stray payment methods not tied to a config (e.g. leftover delivery-provider ones)
        cls.env['pos.payment.method'].search([
            ('company_id', '=', cls.company.id),
            ('config_ids', '=', False),
        ]).unlink()
        cls.cash_pm = cls.env['pos.payment.method'].create({
            'name': 'Cash',
            'type': 'cash',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'journal_id': cls.company_data['default_journal_cash'].id,
            'company_id': cls.env.company.id,
        })
        cls.bank_pm = cls.env['pos.payment.method'].create({
            'name': 'Bank',
            'type': 'bank',
            'journal_id': cls.bank_journal.id,
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
        })
        cls.credit_pm = cls.env['pos.payment.method'].create({
            'name': 'Credit',
            'receivable_account_id': cls.company_data['default_account_receivable'].id,
            'type': 'pay_later',
        })
        # TODO-PARP: Remove these aliases after all modules are migrated.
        cls.cash_payment_method = cls.cash_pm
        cls.bank_payment_method = cls.bank_pm
        cls.credit_payment_method = cls.credit_pm
        cls.cash_pm1 = cls.cash_pm
        cls.bank_pm1 = cls.bank_pm
        cls.pay_later_pm = cls.credit_pm

        cls.cash_pm2 = cls.env['pos.payment.method'].create({
            'name': 'Cash Other',
            'type': 'cash',
            'journal_id': cls.other_cash_journal.id,
            'receivable_account_id': cls.pos_receivable_cash.id,
        })
        cls.bank_pm2 = cls.env['pos.payment.method'].create({
            'name': 'Bank Other',
            'type': 'bank',
            'journal_id': cls.other_bank_journal.id,
            'receivable_account_id': cls.pos_receivable_bank.id,
            'outstanding_account_id': cls.outstanding_bank.id,
        })

    @classmethod
    def _setup_pos_configs(cls):
        cls.pos_config_usd = cls.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
            'tax_regime_selection': True,
            'fiscal_position_ids': [Command.set(cls.fiscal_position_pos.ids)],
            'journal_id': cls.company_data['default_journal_sale'].id,
            'payment_method_ids': [Command.set((cls.bank_pm | cls.cash_pm | cls.credit_pm).ids)],
            'use_pricelist': True,
            'pricelist_id': cls.public_pricelist.id,
            'available_pricelist_ids': [Command.set((cls.http_pricelists - cls.excluded_pricelist).ids)],
        })

        cls.pos_config_eur = cls.env['pos.config'].create({
            'name': 'PoS Config EUR',
            'journal_id': cls.other_sales_journal.id,
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, cls.pricelist_eur.ids)],
            'pricelist_id': cls.pricelist_eur.id,
            'payment_method_ids': [Command.set((cls.bank_pm2 | cls.bank_pm).ids)],
        })
        # TODO-PARP: Remove this alias after all modules are migrated.
        cls.basic_config = cls.pos_config_usd
        cls.config = cls.pos_config_usd
        cls.main_pos_config = cls.pos_config_usd

    @classmethod
    def _setup_attribute_products(cls):
        attribute = cls.env['product.attribute'].create({
            'name': 'add 2',
            'value_ids': [Command.create({'name': 'add 2'})],
        })
        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Red', 'html_color': '#ff0000'}),
                Command.create({'name': 'Wood', 'html_color': '#0000ff'}),
            ],
        })
        cls.chair_legs_attribute = cls.env['product.attribute'].create({
            'name': 'Chair Legs',
            'display_type': 'select',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Metal'}),
                Command.create({'name': 'Wood'}),
            ],
        })
        cls.chair_fabrics_attribute = cls.env['product.attribute'].create({
            'name': 'Fabrics',
            'display_type': 'radio',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Leather'}),
                Command.create({'name': 'wool'}),
                Command.create({'name': 'Other', 'is_custom': True}),
            ],
        })
        cls.chair_addons_attribute = cls.env['product.attribute'].create({
            'name': 'Add-ons',
            'display_type': 'multi',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Cushion'}),
                Command.create({'name': 'Cup Holder'}),
                Command.create({'name': 'Headrest'}),
            ],
        })

        # Whiteboard Pen: a single choice; HTTP setup applies its extra price.
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.whiteboard_pen.id,
            'attribute_id': attribute.id,
            'value_ids': [Command.set(attribute.value_ids.ids)],
        })

        # Chair color picker: red adds 1; blue accepts custom input.
        chair_color_line = cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': cls.color_attribute.id,
            'value_ids': [Command.set(cls.color_attribute.value_ids.ids)],
        })
        chair_color_line.product_template_value_ids[0].price_extra = 1

        # Chair legs dropdown: metal or wood.
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': cls.chair_legs_attribute.id,
            'value_ids': [Command.set(cls.chair_legs_attribute.value_ids.ids)],
        })

        # Chair fabrics radio buttons: leather, wool, or a custom fabric.
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': cls.chair_fabrics_attribute.id,
            'value_ids': [Command.set(cls.chair_fabrics_attribute.value_ids.ids)],
        })
        chair_color_line.product_template_value_ids[1].is_custom = True

        # Chair accessories: allow selecting multiple add-ons.
        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': cls.chair_addons_attribute.id,
            'value_ids': [Command.set(cls.chair_addons_attribute.value_ids.ids)],
        })

    @classmethod
    def _setup_combo_product(cls):
        """Build the office combo from shared products, including the configurable chair."""
        def create_combo(name, items):
            return cls.env['product.combo'].create({
                'name': name,
                'combo_item_ids': [
                    Command.create({'product_id': product.product_variant_id.id, 'extra_price': extra_price})
                    for product, extra_price in items
                ],
            })

        cls.desk_accessories_combo = create_combo('Desk Accessories Combo', [
            (cls.whiteboard_pen, 0),
            (cls.small_shelf, 0),
            (cls.monitor_stand, 2),
        ])
        cls.desks_combo = create_combo('Desks Combo', [
            (cls.wall_shelf, 0),
            (cls.desk_pad, 2),
        ])
        cls.chairs_combo = create_combo('Chairs Combo', [
            (cls.letter_tray, 0),
            (cls.magnetic_board, 0),
            (cls.desk_organizer, 5),
            (cls.configurable_chair, 0),
        ])
        cls.office_combo = cls.create_product(
            'Office Combo', 40,
            type='combo',
            is_storable=False,
            combo_ids=[Command.set((cls.desks_combo | cls.chairs_combo | cls.desk_accessories_combo).ids)],
            pos_categ_ids=[Command.set(cls.pos_cat_desk_test.ids)],
        )

    @classmethod
    def _setup_pricelists(cls):
        def create_pricelist(name, items=(), *, compute_price='fixed', **values):
            return cls.env['product.pricelist'].create({
                'name': name,
                'item_ids': [Command.create({'compute_price': compute_price, **item}) for item in items],
                **values,
            })

        def product_rule(product, **values):
            return {
                'applied_on': '0_product_variant',
                'product_id': product.product_variant_id.id,
                **values,
            }

        cls.pricelist_eur = create_pricelist('Test EUR Pricelist', currency_id=cls.other_currency.id)
        cls.fixed_pricelist = create_pricelist('Fixed', [
            {'fixed_price': 1},
            product_rule(cls.wall_shelf, fixed_price=2),
            product_rule(cls.small_shelf, fixed_price=13.95),  # test for issues like in 7f260ab517ebde634fc274e928eb062463f0d88f
        ])

        cls.http_pricelists = create_pricelist('Percentage', [
            product_rule(cls.wall_shelf, price_discount=100),
            product_rule(cls.small_shelf, price_discount=99),
            product_rule(cls.magnetic_board, price_discount=0),
        ], compute_price='discount')

        cls.http_pricelists |= create_pricelist('Formula', [
            product_rule(cls.wall_shelf, price_discount=6, price_surcharge=5),
            product_rule(cls.small_shelf, price_surcharge=-0.01, price_round=1),  # .99 prices
            product_rule(cls.magnetic_board, price_min_margin=10, price_max_margin=100),
            product_rule(cls.monitor_stand, price_surcharge=10, price_max_margin=5),
            product_rule(cls.desk_pad, price_discount=-100, price_min_margin=5, price_max_margin=20),
        ], compute_price='discount')

        cls.http_pricelists |= create_pricelist('min_quantity ordering', [
            product_rule(cls.wall_shelf, fixed_price=1, min_quantity=2),
            product_rule(cls.wall_shelf, fixed_price=2, min_quantity=1),
            product_rule(cls.monitor_stand, fixed_price=1, min_quantity=5),
        ])

        cls.http_pricelists |= create_pricelist('Product template', [
            {'fixed_price': 1, 'applied_on': '1_product', 'product_tmpl_id': cls.wall_shelf.id},
            {'fixed_price': 2},
        ])

        # No category has precedence over category.
        cls.http_pricelists |= create_pricelist('Category vs no category', [
            {'fixed_price': 1, 'applied_on': '2_product_category', 'categ_id': cls.categ_services.id},
            {'fixed_price': 2},
        ])

        cls.http_pricelists |= create_pricelist('Category', [
            {'fixed_price': 2, 'applied_on': '2_product_category', 'categ_id': cls.categ_basic.id},
            {'fixed_price': 1, 'applied_on': '2_product_category', 'categ_id': cls.categ_services.id},
        ])

        today = date.today()
        one_week_ago = (today - timedelta(weeks=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        two_weeks_ago = (today - timedelta(weeks=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        one_week_from_now = (today + timedelta(weeks=1)).strftime(DEFAULT_SERVER_DATE_FORMAT)
        two_weeks_from_now = (today + timedelta(weeks=2)).strftime(DEFAULT_SERVER_DATE_FORMAT)

        cls.public_pricelist = create_pricelist('Public Pricelist')
        cls.http_pricelists |= create_pricelist('Dates', [
            {'fixed_price': 1, 'date_start': two_weeks_ago, 'date_end': one_week_ago},
            {'fixed_price': 2, 'date_start': today.strftime(DEFAULT_SERVER_DATE_FORMAT), 'date_end': one_week_from_now},
            {'fixed_price': 3, 'date_start': one_week_from_now, 'date_end': two_weeks_from_now},
        ])

        cls.cost_base_pricelist = create_pricelist('Cost base', [{'base': 'standard_price', 'price_discount': 55}], compute_price='discount')
        cls.pricelist_base_pricelist = create_pricelist('Pricelist base', [
            {'base': 'pricelist', 'base_pricelist_id': cls.cost_base_pricelist.id, 'price_discount': 15},
        ], compute_price='discount')
        cls.http_pricelists |= create_pricelist('Pricelist base 2', [
            {'base': 'pricelist', 'base_pricelist_id': cls.pricelist_base_pricelist.id, 'price_discount': 3},
        ], compute_price='discount')
        cls.http_pricelists |= create_pricelist('Pricelist base rounding', [
            {'base': 'pricelist', 'base_pricelist_id': cls.fixed_pricelist.id, 'price_discount': 0.01},
        ], compute_price='discount')

        cls.excluded_pricelist = create_pricelist('Not loaded')
        cls.http_pricelists |= (
            cls.fixed_pricelist | cls.public_pricelist | cls.cost_base_pricelist
            | cls.pricelist_base_pricelist | cls.excluded_pricelist
        )

    @classmethod
    def _setup_fiscal_positions(cls):
        cls.fiscal_position_pos = cls.env['account.fiscal.position'].create({
            'name': 'FP-POS-2M',
        })
