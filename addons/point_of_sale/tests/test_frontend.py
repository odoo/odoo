# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from contextlib import contextmanager
from unittest.mock import patch
from odoo import Command

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from datetime import date, timedelta
from odoo.addons.point_of_sale.tests.common import archive_products
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TestPointOfSaleHttpCommon(AccountTestInvoicingHttpCommon):

    @classmethod
    def _get_main_company(cls):
        return cls.company_data['company']

    def _get_url(self, pos_config=None):
        pos_config = pos_config or self.main_pos_config
        return f"/pos/ui?config_id={pos_config.id}"

    def start_pos_tour(self, tour_name, login="pos_user", **kwargs):
        self.start_tour(self._get_url(pos_config=kwargs.get('pos_config')), tour_name, login=login, **kwargs)

    @contextmanager
    def with_new_session(self, config=None, user=None):
        config = config or self.main_pos_config
        user = user or self.pos_user
        config.with_user(user).open_ui()
        session = config.current_session_id
        yield session
        session.post_closing_cash_details(0)
        session.close_session_from_ui()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        env = cls.env
        cls.env.user.groups_id += env.ref('point_of_sale.group_pos_manager')
        journal_obj = env['account.journal']
        account_obj = env['account.account']
        main_company = cls._get_main_company()

        cls.account_receivable = account_obj.create({'code': 'X1012',
                                                 'name': 'Account Receivable - Test',
                                                 'account_type': 'asset_receivable',
                                                 'reconcile': True})
        env.company.account_default_pos_receivable_account_id = cls.account_receivable
        env['ir.default'].set('res.partner', 'property_account_receivable_id', cls.account_receivable.id, company_id=main_company.id)
        # Pricelists are set below, do not take demo data into account
        env['res.partner'].sudo().invalidate_model(['property_product_pricelist', 'specific_property_product_pricelist'])
        # remove the all specific values for all companies only for test
        env.cr.execute('UPDATE res_partner SET specific_property_product_pricelist = NULL')

        # Create user.
        cls.pos_user = cls.env['res.users'].create({
            'name': 'A simple PoS man!',
            'login': 'pos_user',
            'password': 'pos_user',
            'groups_id': [
                (4, cls.env.ref('base.group_user').id),
                (4, cls.env.ref('point_of_sale.group_pos_user').id),
                (4, cls.env.ref('stock.group_stock_user').id),
            ],
            'tz': 'America/New_York',
        })
        cls.pos_admin = cls.env['res.users'].create({
            'name': 'A powerful PoS man!',
            'login': 'pos_admin',
            'password': 'pos_admin',
            'groups_id': [
                (4, cls.env.ref('point_of_sale.group_pos_manager').id),
            ],
            'tz': 'America/New_York',
        })

        cls.pos_user.partner_id.email = 'pos_user@test.com'
        cls.pos_admin.partner_id.email = 'pos_admin@test.com'

        cls.bank_journal = journal_obj.create({
            'name': 'Bank Test',
            'type': 'bank',
            'company_id': main_company.id,
            'code': 'BNK',
            'sequence': 10,
        })

        cls.bank_payment_method = env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': cls.bank_journal.id,
            'outstanding_account_id': cls.inbound_payment_method_line.payment_account_id.id,
        })
        env['pos.config'].search([]).unlink()
        cls.main_pos_config = env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
        })

        env['res.partner'].create({
            'name': 'Deco Addict',
        })

        cash_journal = journal_obj.create({
            'name': 'Cash Test',
            'type': 'cash',
            'company_id': main_company.id,
            'code': 'CSH',
            'sequence': 10,
        })

        archive_products(env)

        cls.tip = env.ref('point_of_sale.product_product_tip')

        cls.pos_desk_misc_test = env['pos.category'].create({
            'name': 'Misc test',
        })
        cls.pos_cat_chair_test = env['pos.category'].create({
            'name': 'Chair test',
        })
        cls.pos_cat_desk_test = env['pos.category'].create({
            'name': 'Desk test',
        })

        # test an extra price on an attribute
        cls.whiteboard_pen = env['product.template'].create({
            'name': 'Whiteboard Pen',
            'available_in_pos': True,
            'list_price': 1.20,
            'taxes_id': False,
            'weight': 0.01,
            'to_weight': True,
            'pos_categ_ids': [(4, cls.pos_desk_misc_test.id)],
        })
        cls.wall_shelf = env['product.template'].create({
            'name': 'Wall Shelf Unit',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'barcode': '2100005000000',
        })
        cls.small_shelf = env['product.template'].create({
            'name': 'Small Shelf',
            'available_in_pos': True,
            'list_price': 2.83,
            'taxes_id': False,
        })
        cls.magnetic_board = env['product.template'].create({
            'name': 'Magnetic Board',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'barcode': '2305000000004',
        })
        cls.monitor_stand = env['product.template'].create({
            'name': 'Monitor Stand',
            'available_in_pos': True,
            'list_price': 3.19,
            'taxes_id': False,
            'barcode': '0123456789',  # No pattern in barcode nomenclature
        })
        cls.desk_pad = env['product.template'].create({
            'name': 'Desk Pad',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_ids': [(4, cls.pos_cat_desk_test.id)],
        })
        cls.letter_tray = env['product.template'].create({
            'name': 'Letter Tray',
            'available_in_pos': True,
            'list_price': 4.80,
            'taxes_id': False,
            'categ_id': env.ref('product.product_category_services').id,
            'pos_categ_ids': [(4, cls.pos_cat_chair_test.id)],
        })
        cls.desk_organizer = env['product.template'].create({
            'name': 'Desk Organizer',
            'available_in_pos': True,
            'list_price': 5.10,
            'taxes_id': False,
            'barcode': '2300002000007',
        })
        cls.configurable_chair = env['product.template'].create({
            'name': 'Configurable Chair',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        attribute = env['product.attribute'].create({
            'name': 'add 2',
        })
        attribute_value = env['product.attribute.value'].create({
            'name': 'add 2',
            'attribute_id': attribute.id,
        })
        line = env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.whiteboard_pen.id,
            'attribute_id': attribute.id,
            'value_ids': [(6, 0, attribute_value.ids)]
        })
        line.product_template_value_ids[0].price_extra = 2

        chair_color_attribute = env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'color',
            'create_variant': 'no_variant',
        })
        chair_color_red = env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': chair_color_attribute.id,
            'html_color': '#ff0000',
        })
        chair_color_blue = env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': chair_color_attribute.id,
            'html_color': '#0000ff',
        })
        chair_color_line = env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': chair_color_attribute.id,
            'value_ids': [(6, 0, [chair_color_red.id, chair_color_blue.id])]
        })
        chair_color_line.product_template_value_ids[0].price_extra = 1

        chair_legs_attribute = env['product.attribute'].create({
            'name': 'Chair Legs',
            'display_type': 'select',
            'create_variant': 'no_variant',
        })
        chair_legs_metal = env['product.attribute.value'].create({
            'name': 'Metal',
            'attribute_id': chair_legs_attribute.id,
        })
        chair_legs_wood = env['product.attribute.value'].create({
            'name': 'Wood',
            'attribute_id': chair_legs_attribute.id,
        })
        env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': chair_legs_attribute.id,
            'value_ids': [(6, 0, [chair_legs_metal.id, chair_legs_wood.id])]
        })

        chair_fabrics_attribute = env['product.attribute'].create({
            'name': 'Fabrics',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })
        chair_fabrics_leather = env['product.attribute.value'].create({
            'name': 'Leather',
            'attribute_id': chair_fabrics_attribute.id,
        })
        chair_fabrics_wool = env['product.attribute.value'].create({
            'name': 'wool',
            'attribute_id': chair_fabrics_attribute.id,
        })
        chair_fabrics_other = env['product.attribute.value'].create({
            'name': 'Other',
            'attribute_id': chair_fabrics_attribute.id,
            'is_custom': True,
        })
        env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.configurable_chair.id,
            'attribute_id': chair_fabrics_attribute.id,
            'value_ids': [(6, 0, [chair_fabrics_leather.id, chair_fabrics_wool.id, chair_fabrics_other.id])]
        })
        chair_color_line.product_template_value_ids[1].is_custom = True

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

        env['product.pricelist'].create({
            'name': 'Percentage',
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'percent_price': 100,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'percentage',
                'percent_price': 99,
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'percentage',
                'percent_price': 0,
                'applied_on': '0_product_variant',
                'product_id': cls.magnetic_board.product_variant_id.id,
            })],
        })

        env['product.pricelist'].create({
            'name': 'Formula',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'price_discount': 6,
                'price_surcharge': 5,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.product_variant_id.id,
            }), (0, 0, {
                # .99 prices
                'compute_price': 'formula',
                'price_surcharge': -0.01,
                'price_round': 1,
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_min_margin': 10,
                'price_max_margin': 100,
                'applied_on': '0_product_variant',
                'product_id': cls.magnetic_board.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_surcharge': 10,
                'price_max_margin': 5,
                'applied_on': '0_product_variant',
                'product_id': cls.monitor_stand.product_variant_id.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_discount': -100,
                'price_min_margin': 5,
                'price_max_margin': 20,
                'applied_on': '0_product_variant',
                'product_id': cls.desk_pad.product_variant_id.id,
            })],
        })

        env['product.pricelist'].create({
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
            })],
        })

        env['product.pricelist'].create({
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

        product_category_3 = env['product.category'].create({
            'name': 'Services',
            'parent_id': env.ref('product.product_category_services').id,
        })

        env['product.pricelist'].create({
            # no category has precedence over category
            'name': 'Category vs no category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': product_category_3.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })

        env['product.pricelist'].create({
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
                'categ_id': product_category_3.id,
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

        env['product.pricelist'].create({
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
                'compute_price': 'percentage',
                'percent_price': 55,
            })],
        })

        pricelist_base_pricelist = env['product.pricelist'].create({
            'name': 'Pricelist base',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': cost_base_pricelist.id,
                'compute_price': 'percentage',
                'percent_price': 15,
            })],
        })

        env['product.pricelist'].create({
            'name': 'Pricelist base 2',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': pricelist_base_pricelist.id,
                'compute_price': 'percentage',
                'percent_price': 3,
            })],
        })

        env['product.pricelist'].create({
            'name': 'Pricelist base rounding',
            'item_ids': [(0, 0, {
                'base': 'pricelist',
                'base_pricelist_id': fixed_pricelist.id,
                'compute_price': 'percentage',
                'percent_price': 0.01,
            })],
        })

        excluded_pricelist = env['product.pricelist'].create({
            'name': 'Not loaded'
        })
        res_partner_18 = env['res.partner'].create({
            'name': 'Lumber Inc',
            'is_company': True,
        })
        res_partner_18.property_product_pricelist = excluded_pricelist

        test_sale_journal = journal_obj.create({'name': 'Sales Journal - Test',
                                                'code': 'TSJ',
                                                'type': 'sale',
                                                'company_id': main_company.id})

        all_pricelists = env['product.pricelist'].search([
            ('id', '!=', excluded_pricelist.id),
            '|', ('company_id', '=', main_company.id), ('company_id', '=', False)
        ])
        all_pricelists.write(dict(currency_id=main_company.currency_id.id))

        src_tax = env['account.tax'].create({'name': "SRC", 'amount': 10})
        dst_tax = env['account.tax'].create({'name': "DST", 'amount': 5})

        cls.letter_tray.taxes_id = [(6, 0, [src_tax.id])]

        cls.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(0, 0, {
                                            'name': "FP-POS-2M",
                                            'tax_ids': [
                                                (0,0,{'tax_src_id': src_tax.id,
                                                      'tax_dest_id': src_tax.id}),
                                                (0,0,{'tax_src_id': src_tax.id,
                                                      'tax_dest_id': dst_tax.id})]
                                            })],
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
            'payment_method_ids': [(0, 0, { 'name': 'Cash',
                                            'journal_id': cash_journal.id,
                                            'receivable_account_id': cls.account_receivable.id,
            })],
            'use_pricelist': True,
            'pricelist_id': public_pricelist.id,
            'available_pricelist_ids': [(4, pricelist.id) for pricelist in all_pricelists],
        })

        # Set customers
        partners = cls.env['res.partner'].create([
            {'name': 'Partner Test 1'},
            {'name': 'Partner Test 2'},
            {'name': 'Partner Test 3'},
            {
                'name': 'Partner Full',
                'email': 'partner.full@example.com',
                'street': '77 Santa Barbara Rd',
                'city': 'Pleasant Hill',
                'state_id': cls.env.ref('base.state_us_5').id,
                'zip': '94523',
                'country_id': cls.env.ref('base.us').id,
            }
        ])
        cls.partner_test_1 = partners[0]
        cls.partner_test_2 = partners[1]
        cls.partner_test_3 = partners[2]
        cls.partner_full = partners[3]

        # Change the default sale pricelist of customers,
        # so the js tests can expect deterministically this pricelist when selecting a customer.
        # bad hack only for test
        env['ir.default'].set("res.partner", "specific_property_product_pricelist", public_pricelist.id, company_id=main_company.id)


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    def test_01_pos_basic_order(self):
        self.tip.write({
            'taxes_id': False
        })
        self.main_pos_config.write({
            'iface_tipproduct': True,
            'tip_product_id': self.tip.id,
            'ship_later': True
        })

        # Mark a product as favorite to check if it is displayed in first position
        self.whiteboard_pen.write({
            'is_favorite': True
        })

        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_user).open_ui()

        # needed because tests are run before the module is marked as
        # installed. In js web will only load qweb coming from modules
        # that are returned by the backend in module_boot. Without
        # this you end up with js, css but no qweb.
        self.env['ir.module.module'].search([('name', '=', 'point_of_sale')], limit=1).state = 'installed'

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_pricelist', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_basic_order_01_multi_payment_and_change', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_basic_order_02_decimal_order_quantity', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_basic_order_03_tax_position', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FloatingOrderTour', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ProductScreenTour', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenTour', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ReceiptScreenTour', login="pos_user")

        for order in self.env['pos.order'].search([]):
            self.assertEqual(order.state, 'paid', "Validated order has payment of " + str(order.amount_paid) + " and total of " + str(order.amount_total))

        # check if email from ReceiptScreenTour is properly sent
        email_count = self.env['mail.mail'].search_count([('email_to', '=', 'test@receiptscreen.com')])
        self.assertEqual(email_count, 1)

    def test_02_pos_with_invoiced(self):
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ChromeTour', login="pos_user")
        n_invoiced = self.env['pos.order'].search_count([('state', '=', 'invoiced')])
        n_paid = self.env['pos.order'].search_count([('state', '=', 'paid')])
        self.assertEqual(n_invoiced, 1, 'There should be 1 invoiced order.')
        self.assertEqual(n_paid, 2, 'There should be 2 paid order.')
        last_order = self.env['pos.order'].search([], limit=1, order="id desc")
        self.assertEqual(last_order.lines[0].price_subtotal, 30.0)
        self.assertEqual(last_order.lines[0].price_subtotal_incl, 30.0)

    def test_04_product_configurator(self):
        # Making one attribute inactive to verify that it doesn't show
        configurable_product = self.env['product.product'].search([('name', '=', 'Configurable Chair'), ('available_in_pos', '=', 'True')], limit=1)
        fabrics_line = configurable_product.attribute_line_ids[2]
        fabrics_line.product_template_value_ids[1].ptav_active = False
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('ProductConfiguratorTour')

    def test_05_ticket_screen(self):
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'TicketScreenTour', login="pos_user")

    def test_product_information_screen_admin(self):
        '''Consider this test method to contain a test tour with miscellaneous tests/checks that require admin access.
        '''
        self.product_a.available_in_pos = True
        self.pos_admin.write({
            'groups_id': [Command.link(self.env.ref('base.group_system').id)],
        })
        self.assertFalse(self.product_a.is_storable)
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'CheckProductInformation', login="pos_admin")

    def test_fixed_tax_negative_qty(self):
        """ Assert the negative amount of a negative-quantity orderline
            with zero-amount product with fixed tax.
        """

        # setup the zero-amount product
        tax_received_account = self.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'account_type': 'asset_current',
        })
        fixed_tax = self.env['account.tax'].create({
            'name': 'fixed amount tax',
            'amount_type': 'fixed',
            'amount': 1,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'account_id': tax_received_account.id,
                }),
            ],
            'price_include_override': 'tax_excluded',
        })
        zero_amount_product = self.env['product.product'].create({
            'name': 'Zero Amount Product',
            'available_in_pos': True,
            'list_price': 0,
            'taxes_id': [(6, 0, [fixed_tax.id])],
            'categ_id': self.env.ref('product.product_category_services').id,
        })

        # Make an order with the zero-amount product from the frontend.
        # We need to do this because of the fix in the "compute_all" port.
        self.main_pos_config.write({'iface_tax_included': 'total'})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FixedTaxNegativeQty', login="pos_user")
        pos_session = self.main_pos_config.current_session_id

        # Close the session and check the session journal entry.
        pos_session.action_pos_session_validate()

        lines = pos_session.move_id.line_ids.sorted('balance')

        # order in the tour is paid using the bank payment method.
        bank_pm = self.main_pos_config.payment_method_ids.filtered(lambda pm: pm.name == 'Bank')

        self.assertEqual(lines[0].account_id, bank_pm.receivable_account_id or self.env.company.account_default_pos_receivable_account_id)
        self.assertAlmostEqual(lines[0].balance, -1)
        self.assertEqual(lines[1].account_id, self.env.company.income_account_id)
        self.assertAlmostEqual(lines[1].balance, 0)
        self.assertEqual(lines[2].account_id, tax_received_account)
        self.assertAlmostEqual(lines[2].balance, 1)

    def test_change_without_cash_method(self):
        #create bank payment method
        bank_pm = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
            'is_cash_count': False,
            'split_transactions': False,
            'company_id': self.env.company.id,
        })
        self.main_pos_config.write({'payment_method_ids': [(6, 0, bank_pm.ids)], 'ship_later': True})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenTour2', login="pos_user")

    def test_rounding_up(self):
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding up',
            'rounding': 0.05,
            'rounding_method': 'UP',
        })

        self.env['product.product'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
        })

        self.main_pos_config.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenRoundingUp', login="pos_user")

    def test_rounding_down(self):
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding down',
            'rounding': 0.05,
            'rounding_method': 'DOWN',
        })

        self.env['product.product'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
        })

        self.main_pos_config.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenRoundingDown', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenTotalDueWithOverPayment', login="pos_user")

    def test_rounding_half_up(self):
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding HALF-UP',
            'rounding': 0.5,
            'rounding_method': 'HALF-UP',
        })

        self.env['product.product'].create({
            'name': 'Product Test 1.2',
            'available_in_pos': True,
            'list_price': 1.2,
            'taxes_id': False,
        })

        self.env['product.product'].create({
            'name': 'Product Test 1.25',
            'available_in_pos': True,
            'list_price': 1.25,
            'taxes_id': False,
        })

        self.env['product.product'].create({
            'name': 'Product Test 1.4',
            'available_in_pos': True,
            'list_price': 1.4,
            'taxes_id': False,
        })

        self.main_pos_config.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenRoundingHalfUp', login="pos_user")

    def test_pos_closing_cash_details(self):
        """Test cash difference *loss* at closing.
        """
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id
        current_session.post_closing_cash_details(0)
        current_session.close_session_from_ui()
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'CashClosingDetails', login="pos_user")
        cash_diff_line = self.env['account.bank.statement.line'].search([
            ('payment_ref', 'ilike', 'Cash difference observed during the counting (Loss)')
        ])
        self.assertAlmostEqual(cash_diff_line.amount, -1.00)

    def test_cash_payments_should_reflect_on_next_opening(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'OrderPaidInCash', login="pos_user")

    def test_fiscal_position_no_tax(self):
        #create a tax of 15% with price included
        tax = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 15,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        #create a product with the tax
        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'taxes_id': [(6, 0, [tax.id])],
            'list_price': 100,
            'available_in_pos': True,
        })

        #create a fiscal position that map the tax to no tax
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'No Tax',
            'tax_ids': [(0, 0, {
                'tax_src_id': tax.id,
                'tax_dest_id': False,
            })],
        })

        pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })

        self.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [fiscal_position.id])],
            'available_pricelist_ids': [(6, 0, [pricelist.id])],
            'pricelist_id': pricelist.id,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionNoTax', login="pos_user")

    def test_fiscal_position_inclusive_and_exclusive_tax(self):
        """ Test the mapping of fiscal position for both Tax Inclusive ans Tax Exclusive"""
        # create a tax with price included
        tax_inclusive_1 = self.env['account.tax'].create({
            'name': 'Tax incl.20%',
            'amount': 20,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        tax_exclusive_1 = self.env['account.tax'].create({
            'name': 'Tax excl.20%',
            'amount': 20,
            'price_include_override': 'tax_excluded',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        tax_inclusive_2 = self.env['account.tax'].create({
            'name': 'Tax incl.10%',
            'amount': 10,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        tax_exclusive_2 = self.env['account.tax'].create({
            'name': 'Tax excl.10%',
            'amount': 10,
            'price_include_override': 'tax_excluded',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        self.test_product_1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'available_in_pos': True,
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_inclusive_1.id])],
        })

        self.test_product_2 = self.env['product.product'].create({
            'name': 'Test Product 2',
            'available_in_pos': True,
            'list_price': 100,
            'taxes_id': [(6, 0, [tax_exclusive_1.id])],
        })

        # create a fiscal position that map the tax
        fiscal_position_1 = self.env['account.fiscal.position'].create({
            'name': 'Incl. to Incl.',
            'tax_ids': [(0, 0, {
                'tax_src_id': tax_inclusive_1.id,
                'tax_dest_id': tax_inclusive_2.id,
            })],
        })
        fiscal_position_2 = self.env['account.fiscal.position'].create({
            'name': 'Incl. to Excl.',
            'tax_ids': [(0, 0, {
                'tax_src_id': tax_inclusive_1.id,
                'tax_dest_id': tax_exclusive_2.id,
            })],
        })
        fiscal_position_3 = self.env['account.fiscal.position'].create({
            'name': 'Excl. to Excl.',
            'tax_ids': [(0, 0, {
                'tax_src_id': tax_exclusive_1.id,
                'tax_dest_id': tax_exclusive_2.id,
            })],
        })
        fiscal_position_4 = self.env['account.fiscal.position'].create({
            'name': 'Excl. to Incl.',
            'tax_ids': [(0, 0, {
                'tax_src_id': tax_exclusive_1.id,
                'tax_dest_id': tax_inclusive_2.id,
            })],
        })

        # add the fiscal position to the PoS
        self.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [
                    fiscal_position_1.id,
                    fiscal_position_2.id,
                    fiscal_position_3.id,
                    fiscal_position_4.id,
                ])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionIncl', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionExcl', login="pos_user")

    def test_06_pos_discount_display_with_multiple_pricelist(self):
        """ Test the discount display on the POS screen when multiple pricelists are used."""
        test_product = self.env['product.template'].create({
            'name': 'Test Product',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        base_pricelist = self.env['product.pricelist'].create({
            'name': 'base_pricelist',
        })

        self.env['product.pricelist.item'].create({
            'pricelist_id': base_pricelist.id,
            'product_tmpl_id': test_product.id,
            'compute_price': 'percentage',
            'applied_on': '1_product',
            'percent_price': 30,
        })

        special_pricelist = self.env['product.pricelist'].create({
            'name': 'special_pricelist',
        })
        self.env['product.pricelist.item'].create({
            'pricelist_id': special_pricelist.id,
            'base': 'pricelist',
            'base_pricelist_id': base_pricelist.id,
            'compute_price': 'percentage',
            'applied_on': '3_global',
            'percent_price': 10,
        })

        self.main_pos_config.write({
            'pricelist_id': base_pricelist.id,
            'available_pricelist_ids': [(6, 0, [base_pricelist.id, special_pricelist.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ReceiptScreenDiscountWithPricelistTour', login="pos_user")

    def test_07_product_combo(self):
        setup_product_combo_items(self)
        self.office_combo.write({'lst_price': 50})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('ProductComboPriceTaxIncludedTour')
        order = self.env['pos.order'].search([])
        self.assertEqual(len(order.lines), 4, "There should be 4 order lines - 1 combo parent and 3 combo lines")
        # check that the combo lines are correctly linked to each other
        parent_line_id = self.env['pos.order.line'].search([('product_id.name', '=', 'Office Combo'), ('order_id', '=', order.id)])
        combo_line_ids = self.env['pos.order.line'].search([('product_id.name', '!=', 'Office Combo'), ('order_id', '=', order.id)])
        self.assertEqual(parent_line_id.combo_line_ids, combo_line_ids, "The combo parent should have 3 combo lines")
        # In the future we might want to test also if:
        #   - the combo lines are correctly stored in and restored from local storage
        #   - the combo lines are correctly shared between the pos configs ( in cross ordering )

    def test_07_pos_barcodes_scan(self):
        barcode_rule = self.env.ref("point_of_sale.barcode_rule_client")
        barcode_rule.pattern = barcode_rule.pattern + "|234"
        # should in theory be changed in the JS code to `|^234`
        # If not, it will fail as it will mistakenly match with the product barcode "0123456789"

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'BarcodeScanningTour', login="pos_user")

    def test_08_show_tax_excluded(self):
        # define a tax included tax record
        tax = self.env['account.tax'].create({
            'name': 'Tax 10% Included',
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
        })

        # define a product record with the tax
        self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 110,
            'taxes_id': [(6, 0, [tax.id])],
            'available_in_pos': True,
        })

        # set Tax-Excluded Price
        self.main_pos_config.write({
            'iface_tax_included': 'subtotal'
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ShowTaxExcludedTour', login="pos_user")

    def test_chrome_without_cash_move_permission(self):
        self.env.user.write({'groups_id': [
            Command.set(
                [
                    self.env.ref('base.group_user').id,
                    self.env.ref('point_of_sale.group_pos_user').id,
                ]
            )
        ]})
        self.main_pos_config.open_ui()
        self.start_pos_tour('chrome_without_cash_move_permission', login="accountman")

    def test_09_pos_barcodes_scan_product_packaging(self):
        pack_of_10 = self.env['uom.uom'].create({
            'name': 'Pack of 10',
            'relative_factor': 10,
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_pos_groupable': True,
        })
        product = self.env['product.product'].create({
            'name': 'Packaging Product',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'barcode': '12345601',
            'uom_ids': [Command.link(pack_of_10.id)],
        })
        self.env['product.uom'].create({
            'barcode': '12345610',
            'product_id': product.id,
            'uom_id': pack_of_10.id,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'BarcodeScanningProductPackagingTour', login="pos_user")

    def test_GS1_pos_barcodes_scan(self):
        barcodes_gs1_nomenclature = self.env.ref("barcodes_gs1_nomenclature.default_gs1_nomenclature")
        self.main_pos_config.company_id.write({
            'nomenclature_id': barcodes_gs1_nomenclature.id
        })

        self.env['product.product'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'barcode': '08431673020125',
        })

        self.env['product.product'].create({
            'name': 'Product 2',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'barcode': '08431673020126',
        })

        # 3760171283370 can be parsed with GS1 rules but it's not GS1
        self.env['product.product'].create({
            'name': 'Product 3',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'barcode': '3760171283370',
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'GS1BarcodeScanningTour', login="pos_user")

    def test_refund_order_with_fp_tax_included(self):
        #create a tax of 15% tax included
        self.tax1 = self.env['account.tax'].create({
            'name': 'Tax 1',
            'amount': 15,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
        })
        #create a tax of 0%
        self.tax2 = self.env['account.tax'].create({
            'name': 'Tax 2',
            'amount': 0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
        })
        #create a fiscal position with the two taxes
        self.fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'No Tax',
            'tax_ids': [(0, 0, {
                'tax_src_id': self.tax1.id,
                'tax_dest_id': self.tax2.id,
            })],
        })

        self.product_test = self.env['product.product'].create({
            'name': 'Product Test',
            'is_storable': True,
            'available_in_pos': True,
            'list_price': 100,
            'taxes_id': [(6, 0, self.tax1.ids)],
        })

        #add the fiscal position to the PoS
        self.main_pos_config.write({
            'fiscal_position_ids': [(4, self.fiscal_position.id)],
            'tax_regime_selection': True,
            })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionNoTaxRefund', login="pos_user")

    def test_lot_refund(self):

        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'LotRefundTour', login="pos_user")

    def test_receipt_tracking_method(self):
        self.product_a = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ReceiptTrackingMethodTour', login="pos_user")

    def test_limited_product_pricelist_loading(self):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', '1')

        limited_category = self.env['pos.category'].create({
            'name': 'Limited Category',
        })
        product_1 = self.env['product.product'].create({
            'name': 'Test Product 1',
            'list_price': 100,
            'barcode': '0100100',
            'taxes_id': False,
            'pos_categ_ids': [(4, limited_category.id)],
            'available_in_pos': True,
        })

        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 4,
            'value_ids': [(0, 0, {
                'name': 'White',
                'sequence': 1,
            }), (0, 0, {
                'name': 'Red',
                'sequence': 2,
                'default_extra_price': 50,
            })],
        })

        product_2_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'list_price': 200,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [(4, limited_category.id)],
            'attribute_line_ids': [(0, 0, {
                'attribute_id': color_attribute.id,
                'value_ids': [(6, 0, color_attribute.value_ids.ids)]
            })],
        })

        # Check that two product variant are created
        self.assertEqual(product_2_template.product_variant_count, 2)
        product_2_template.product_variant_ids[0].write({'barcode': '0100201'})
        product_2_template.product_variant_ids[1].write({'barcode': '0100202'})

        self.env['product.product'].create({
            'name': 'Test Product 3',
            'list_price': 300,
            'barcode': '0100300',
            'taxes_id': False,
            'pos_categ_ids': [(4, limited_category.id)],
            'available_in_pos': True,
        })

        pricelist_item = self.env['product.pricelist.item'].create([{
            'applied_on': '3_global',
            'fixed_price': 50,
        }, {
            'applied_on': '1_product',
            'product_tmpl_id': product_2_template.id,
            'fixed_price': 100,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_1.id,
            'fixed_price': 80,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_2_template.product_variant_ids[1].id,
            'fixed_price': 120,
        }])
        self.main_pos_config.write({
            'iface_available_categ_ids': [],
            'limit_categories': True,
        })
        self.main_pos_config.pricelist_id.write({'item_ids': [(6, 0, pricelist_item.ids)]})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'limitedProductPricelistLoading', login="pos_user")

    def test_multi_product_options(self):
        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
        })

        chair_multi_attribute = self.env['product.attribute'].create({
            'name': 'Multi',
            'display_type': 'multi',
            'create_variant': 'no_variant',
        })
        chair_multi_value_1 = self.env['product.attribute.value'].create({
            'name': 'Value 1',
            'attribute_id': chair_multi_attribute.id,
        })
        chair_multi_value_2 = self.env['product.attribute.value'].create({
            'name': 'Value 2',
            'attribute_id': chair_multi_attribute.id,
        })
        self.chair_multi_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_a.product_tmpl_id.id,
            'attribute_id': chair_multi_attribute.id,
            'value_ids': [(6, 0, [chair_multi_value_1.id, chair_multi_value_2.id])]
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'MultiProductOptionsTour', login="pos_user")

    def test_translate_product_name(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.pos_user.write({'lang': 'fr_FR'})

        product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100,
            'taxes_id': False,
            'available_in_pos': True,
        })
        product.update_field_translations('name', {'fr_FR': 'Testez le produit'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'TranslateProductNameTour', login="pos_user")

    def test_properly_display_price(self):
        """Make sure that when the decimal separator is a comma, the shown orderline price is correct.
        """
        lang = self.env['res.lang'].search([('code', '=', self.pos_user.lang)])
        lang.write({'thousands_sep': '.', 'decimal_point': ','})

        self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 1_453.53,
            'taxes_id': False,
            'available_in_pos': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, "DecimalCommaOrderlinePrice", login="pos_user")

    def test_res_partner_scan_barcode(self):
        # default Customer Barcodes pattern is '042'
        self.env['res.partner'].create({
            'name': 'John Doe',
            'barcode': '0421234567890',
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'BarcodeScanPartnerTour', login="pos_user")

    def test_allow_order_modification_after_validation_error(self):
        """
        User error as a result of validation should block the order.
        Taking action by order modification should be allowed.
        """

        self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 10.00,
            'taxes_id': False,
            'available_in_pos': True,
        })

        def sync_from_ui_patch(*_args, **_kwargs):
            raise UserError('Test Error')

        with patch.object(self.env.registry.models['pos.order'], "sync_from_ui", sync_from_ui_patch):
            # If there is problem in the tour, remove the log catcher to debug.
            with self.assertLogs(level="WARNING") as log_catcher:
                self.main_pos_config.with_user(self.pos_user).open_ui()
                self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'OrderModificationAfterValidationError', login="pos_user")

            warning_outputs = [o for o in log_catcher.output if 'WARNING' in o]
            self.assertEqual(len(warning_outputs), 1, "Exactly one warning should be logged")

    def test_customer_display(self):
        self.start_tour(f"/pos_customer_display/{self.main_pos_config.id}/{self.main_pos_config.access_token}", 'CustomerDisplayTour', login="pos_user")

    def test_refund_few_quantities(self):
        """ Test to check that refund works with quantities of less than 0.5 """
        self.env['product.product'].create({
            'name': 'Sugar',
            'list_price': 3,
            'taxes_id': False,
            'available_in_pos': True,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'RefundFewQuantities', login="pos_user")

    def test_product_combo_price(self):
        """ Check that the combo has the expected price """
        self.desk_organizer.product_variant_id.write({"lst_price": 7})
        self.desk_pad.product_variant_id.write({"lst_price": 2.5})
        self.whiteboard_pen.product_variant_id.write({"lst_price": 1.5})

        combos = self.env["product.combo"].create([
            {
                "name": product.name,
                "combo_item_ids": [
                    Command.create({
                        "product_id": product.id, "extra_price": 0
                    })
                ]
            }
            for product in (self.desk_organizer.product_variant_id, self.desk_pad.product_variant_id, self.whiteboard_pen.product_variant_id)
        ])

        self.env["product.product"].create(
            {
                "available_in_pos": True,
                "list_price": 7,
                "standard_price": 10,
                "name": "Desk Combo",
                "type": "combo",
                "taxes_id": False,
                "combo_ids": [
                    (6, 0, [combo.id for combo in combos])
                ],
            }
        )

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'ProductComboPriceCheckTour', login="pos_user")
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.type == 'combo').margin, 0)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.type == 'combo').margin_percent, 0)

    def test_customer_display_as_public(self):
        self.main_pos_config.customer_display_type = 'remote'
        self.main_pos_config.customer_display_bg_img = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        response = self.url_open(f"/web/image/pos.config/{self.main_pos_config.id}/customer_display_bg_img")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Shop.png' in response.headers['Content-Disposition'])

    def test_customer_all_fields_displayed(self):
        """
        Verify that all the field of a partner can be displayed in the partner list.
        Also verify that all these fields can be searched.
        """
        self.env["res.partner"].create({
            "name": "John Doe",
            "street": "1 street of astreet",
            "city": "Acity",
            "state_id": self.env.ref("base.state_us_30").id,  # Ohio
            "country_id": self.env.ref("base.us").id,
            "zip": "26432685463",
            "phone": "1234567890",
            "mobile": "0987654321",
            "email": "john@doe.com"
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PosCustomerAllFieldsDisplayed')

    def test_product_combo_change_fp(self):
        """
        Verify than when the fiscal position is changed,
        the price of the combo doesn't change and taxes are well taken into account
        """
        tax_1 = self.env['account.tax'].create({
            'name': 'Tax 10%',
            'amount': 10,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        tax_2 = self.env['account.tax'].create({
            'name': 'Tax 5%',
            'amount': 5,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        setup_product_combo_items(self)
        self.office_combo.write({'list_price': 50, 'taxes_id': [(6, 0, [tax_1.id])]})
        for combo in self.office_combo.combo_ids:  # Set the tax to all the products of the combo
            for item in combo.combo_item_ids:
                item.product_id.taxes_id = [(6, 0, [tax_1.id])]

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'test fp',
            'tax_ids': [(0, 0, {
                'tax_src_id': tax_1.id,
                'tax_dest_id': tax_2.id,
            })],
        })

        self.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [fiscal_position.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'ProductComboChangeFP', login="pos_user")

    def test_cash_rounding_payment(self):
        """Verify than an error popup is shown if the payment value is more precise than the rounding method"""
        rounding_method = self.env['account.cash.rounding'].create({
            'name': 'Down 0.10',
            'rounding': 0.10,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].copy().id,
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
            'rounding_method': 'DOWN',
        })

        self.main_pos_config.write({
            'cash_rounding': True,
            'only_round_cash_method': False,
            'rounding_method': rounding_method.id,
        })

        self.env['ir.config_parameter'].sudo().set_param('barcode.max_time_between_keys_in_ms', 1)
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'CashRoundingPayment', login="accountman")

    def test_product_categories_order(self):
        """ Verify that the order of categories doesnt change in the frontend """
        self.env['pos.category'].search([]).write({'sequence': 100})
        self.env['pos.category'].create({
            'name': 'AAA',
            'parent_id': False,
            'sequence': 1,
        })
        self.env['pos.category'].create({
            'name': 'AAC',
            'parent_id': False,
            'sequence': 3,
        })
        parentA = self.env['pos.category'].create({
            'name': 'AAB',
            'parent_id': False,
            'sequence': 2,
        })
        parentB = self.env['pos.category'].create({
            'name': 'AAX',
            'parent_id': parentA.id,
        })
        self.env['pos.category'].create({
            'name': 'AAY',
            'parent_id': parentB.id,
        })
        # Add a product that belongs to both parent and child categories.
        # It's presence is checked during the tour to make sure app doesn't crash.
        self.env['product.product'].create({
            'name': 'Product in AAB and AAX',
            'pos_categ_ids': [(6, 0, [parentA.id, parentB.id])],
            'available_in_pos': True,
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'PosCategoriesOrder', login="pos_admin")

    def test_product_with_dynamic_attributes(self):
        dynamic_attribute = self.env['product.attribute'].create({
            'name': 'Dynamic Attribute',
            'create_variant': 'dynamic',
        })
        value_1 = self.env['product.attribute.value'].create({
            'name': 'Test 1',
            'attribute_id': dynamic_attribute.id,
        })
        value_2 = self.env['product.attribute.value'].create({
            'name': 'Test 2',
            'default_extra_price': 10,
            'attribute_id': dynamic_attribute.id,
        })
        product_template = self.env['product.template'].create({
            'name': 'Dynamic Product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'available_in_pos': True,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': dynamic_attribute.id,
            'value_ids': [Command.set([value_1.id, value_2.id])],
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'PosProductWithDynamicAttributes', login="pos_admin")

    def test_autofill_cash_count(self):
        """Make sure that when the decimal separator is a comma, the shown orderline price is correct.
        """
        lang = self.env['res.lang'].search([('code', '=', self.pos_user.lang)])
        lang.write({'thousands_sep': '.', 'decimal_point': ','})
        self.env["product.product"].create(
            {
                "available_in_pos": True,
                "list_price": 123456,
                "name": "Test Expensive",
                "taxes_id": False
            }
        )
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, "AutofillCashCount", login="pos_user")

    def test_lot(self):
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'LotTour', login="pos_user")


    def test_product_search(self):
        """Verify that the product search works correctly"""
        self.env['product.product'].create([
            {
                'name': 'Test Product 1',
                'list_price': 100,
                'taxes_id': False,
                'available_in_pos': True,
                'barcode': '1234567890123',
                'default_code': 'TESTPROD1',
            },
            {
                'name': 'Test Product 2',
                'list_price': 100,
                'taxes_id': False,
                'available_in_pos': True,
                'barcode': '1234567890124',
                'default_code': 'TESTPROD2',
            },
            {
                'name': 'Apple',
                'list_price': 100,
                'taxes_id': False,
                'available_in_pos': True,
            },
        ])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ProductSearchTour', login="pos_user")

    def test_sort_orderlines_by_product_categoryies(self):
        """ Test to ensure orderlines are added to the cart in the correct order based on their categories"""
        self.pos_desk_misc_test.write({'sequence': 0})
        self.pos_cat_chair_test.write({'sequence': 1})

        self.product_1_categ_seq_1 = self.env['product.template'].create({
            'name': 'Product_1 Category sequence 1',
            'available_in_pos': True,
            'list_price': 1.00,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.pos_desk_misc_test.id)],
        })
        self.product_2_categ_seq_1 = self.env['product.template'].create({
            'name': 'Product_2 Category sequence 1',
            'available_in_pos': True,
            'list_price': 2.00,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.pos_desk_misc_test.id)],
        })
        self.product_11_categ_seq_2 = self.env['product.template'].create({
            'name': 'Product_11 Category sequence 2',
            'available_in_pos': True,
            'list_price': 3.00,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.pos_cat_chair_test.id)],
        })
        self.product_22_categ_seq_2 = self.env['product.template'].create({
            'name': 'Product_22 Category sequence 2',
            'available_in_pos': True,
            'list_price': 4.00,
            'taxes_id': False,
            'pos_categ_ids': [(4, self.pos_cat_chair_test.id)],
        })

        self.main_pos_config.write({
            'orderlines_sequence_in_cart_by_category': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'SortOrderlinesByCategories', login="pos_user")

# This class just runs the same tests as above but with mobile emulation
class MobileTestUi(TestUi):
    browser_size = '375x667'
    touch_enabled = True
    allow_inherited_tests_method = True
