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

        cls.env['ir.default'].set(
            'res.partner', 'property_account_receivable_id',
            cls.pos_receivable_account.id, company_id=cls.company.id,
        )
        # Pricelists are set below, do not take demo data into account.
        cls.env['res.partner'].sudo().invalidate_model([
            'property_product_pricelist', 'specific_property_product_pricelist',
        ])
        # Remove specific pricelists for all companies in the test transaction.
        cls.env.cr.execute('UPDATE res_partner SET specific_property_product_pricelist = NULL')

        cls._setup_account_journals()
        cls._setup_payment_methods()
        cls._setup_categories()
        cls._setup_taxes()
        cls._setup_pos_products()
        cls._setup_pricelists()
        cls._setup_customers()
        cls._setup_pos_configs()

        cls._setup_attribute_products()
        cls._setup_fiscal_positions()
        cls._setup_printers()

        # TODO-PARP:
        # cls._setup_combo_product()  # will replace setup_product_combo_items

    @classmethod
    def _archive_products(cls):
        # Preserve fixtures created by another test base with the independent test user.
        cls.env['product.template'].search([
            ('available_in_pos', '=', True),
            ('create_uid', '!=', cls.env.uid),
        ])._write({'active': False})

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
        cls.cat_no_tax, cls.cat_tax_five_incl, cls.cat_tax_ten_incl, cls.cat_tax_fifteen_incl = cls.env['pos.category'].create([
            {'name': 'No tax', 'sequence': 0},
            {'name': 'Tax five incl', 'sequence': 1},
            {'name': 'Tax ten incl', 'sequence': 2},
            {'name': 'Tax fifteen incl', 'sequence': 3},
        ])
        # Product Categories
        cls.categ_basic = cls.env.ref('product.product_category_services')
        cls.categ_services = cls.env['product.category'].create({
            'name': 'Services',
            'parent_id': cls.categ_basic.id,
        })
        cls.pos_desk_misc_test = cls.cat_no_tax
        cls.pos_cat_chair_test = cls.cat_tax_five_incl
        cls.pos_cat_desk_test = cls.cat_tax_ten_incl

    @classmethod
    def _setup_pos_products(cls):
        cls.ten_dollars_no_tax = cls.create_product_template('Ten dollars no tax', 10.0, [cls.cat_no_tax.id])
        cls.twenty_dollars_no_tax = cls.create_product_template('Twenty dollars no tax', 20.0, [cls.cat_no_tax.id])
        cls.ten_dollars_with_5_incl = cls.create_product_template('Ten dollars with 5 included', 10.0, [cls.cat_tax_five_incl.id], [cls.taxes['tax5_incl'].id])
        cls.twenty_dollars_with_5_incl = cls.create_product_template('Twenty dollars with 5 included', 20.0, [cls.cat_tax_five_incl.id], [cls.taxes['tax5_incl'].id])
        cls.ten_dollars_with_10_incl = cls.create_product_template('Ten dollars with 10 included', 10.0, [cls.cat_tax_ten_incl.id], [cls.taxes['tax10_incl'].id])
        cls.twenty_dollars_with_10_incl = cls.create_product_template('Twenty dollars with 10 included', 20.0, [cls.cat_tax_ten_incl.id], [cls.taxes['tax10_incl'].id])
        cls.ten_dollars_with_15_incl = cls.create_product_template('Ten dollars with 15 included', 10.0, [cls.cat_tax_fifteen_incl.id], [cls.taxes['tax15_incl'].id])
        cls.twenty_dollars_with_15_incl = cls.create_product_template('Twenty dollars with 15 included', 20.0, [cls.cat_tax_fifteen_incl.id], [cls.taxes['tax15_incl'].id])

        # HTTP tests adapt these records to their tour names and prices.
        cls.whiteboard_pen = cls.ten_dollars_no_tax
        cls.wall_shelf = cls.twenty_dollars_no_tax
        cls.small_shelf = cls.ten_dollars_with_5_incl
        cls.magnetic_board = cls.twenty_dollars_with_5_incl
        cls.monitor_stand = cls.ten_dollars_with_10_incl
        cls.desk_pad = cls.twenty_dollars_with_10_incl
        cls.letter_tray = cls.ten_dollars_with_15_incl
        cls.desk_organizer = cls.twenty_dollars_with_15_incl
        cls.configurable_chair = cls.create_product_template('Configurable Chair', 10.0, available_in_pos=False)
        cls.vanela_gathiya = cls.create_product_template('Vanela Gathiya', 10.0, available_in_pos=False, to_weight=True)

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
            'journal_id': cls.company_data['default_journal_bank'].id,
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
            'name': 'PoS Config USD',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'payment_method_ids': [
                (4, cls.credit_pm.id),
                (4, cls.bank_pm.id),
                (4, cls.cash_pm.id),
            ],
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
    def _setup_pricelists(cls):
        env = cls.env
        cls.pricelist_eur = cls.env['product.pricelist'].create({
            'name': 'Test EUR Pricelist',
            'currency_id': cls.other_currency.id,
        })

        cls.http_pricelists = env['product.pricelist']
        fixed_pricelist = env['product.pricelist'].create({
            'name': 'Fixed',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 13.95,  # test for issues like in 7f260ab517ebde634fc274e928eb062463f0d88f
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.product_variant_id.id,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'Percentage',
            'item_ids': [(0, 0, {
                'compute_price': 'discount',
                'price_discount': 100,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'discount',
                'price_discount': 99,
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'discount',
                'price_discount': 0,
                'applied_on': '0_product_variant',
                'product_id': cls.magnetic_board.product_variant_id.id,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'Formula',
            'item_ids': [(0, 0, {
                'compute_price': 'discount',
                'price_discount': 6,
                'price_surcharge': 5,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                # .99 prices
                'compute_price': 'discount',
                'price_surcharge': -0.01,
                'price_round': 1,
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'discount',
                'price_min_margin': 10,
                'price_max_margin': 100,
                'applied_on': '0_product_variant',
                'product_id': cls.magnetic_board.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'discount',
                'price_surcharge': 10,
                'price_max_margin': 5,
                'applied_on': '0_product_variant',
                'product_id': cls.monitor_stand.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'discount',
                'price_discount': -100,
                'price_min_margin': 5,
                'price_max_margin': 20,
                'applied_on': '0_product_variant',
                'product_id': cls.desk_pad.product_variant_id.id,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'min_quantity ordering',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '0_product_variant',
                'min_quantity': 2,
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '0_product_variant',
                'min_quantity': 1,
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '0_product_variant',
                'min_quantity': 5,
                'product_id': cls.monitor_stand.product_variant_id.id,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'Product template',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '1_product',
                'product_tmpl_id': cls.wall_shelf.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            # no category has precedence over category
            'name': 'Category vs no category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': cls.categ_services.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'Category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '2_product_category',
                'categ_id': env.ref('product.product_category_services').id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': cls.categ_services.id,
            })],
        })

        today = date.today()
        one_week_ago = today - timedelta(weeks=1)
        two_weeks_ago = today - timedelta(weeks=2)
        one_week_from_now = today + timedelta(weeks=1)
        two_weeks_from_now = today + timedelta(weeks=2)

        public_pricelist = env['product.pricelist'].create({
            'name': 'Public Pricelist',
        })

        cls.http_pricelists |= env['product.pricelist'].create({
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

        cost_base_pricelist = env['product.pricelist'].create({
            'name': 'Cost base',
            'item_ids': [(0, 0, {
                'base': 'standard_price',
                'compute_price': 'discount',
                'price_discount': 55,
            })],
        })

        pricelist_base_pricelist = env['product.pricelist'].create({
            'name': 'Pricelist base',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': cost_base_pricelist.id,
                'compute_price': 'discount',
                'price_discount': 15,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'Pricelist base 2',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': pricelist_base_pricelist.id,
                'compute_price': 'discount',
                'price_discount': 3,
            })],
        })

        cls.http_pricelists |= env['product.pricelist'].create({
            'name': 'Pricelist base rounding',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': fixed_pricelist.id,
                'compute_price': 'discount',
                'price_discount': 0.01,
            })],
        })

        excluded_pricelist = env['product.pricelist'].create({
            'name': 'Not loaded'
        })
        cls.public_pricelist = public_pricelist
        cls.excluded_pricelist = excluded_pricelist
        cls.http_pricelists |= fixed_pricelist | public_pricelist | cost_base_pricelist | pricelist_base_pricelist | excluded_pricelist

    @classmethod
    def _setup_fiscal_positions(cls):
        cls.fiscal_position_pos = cls.env['account.fiscal.position'].create({
            'name': 'FP-POS-2M',
        })

    @classmethod
    def _setup_printers(cls):
        cls.printer = cls.env['pos.printer'].create({
            'name': 'Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '0.0.0.0',
            'use_type': 'receipt',
        })
