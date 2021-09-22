# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
from odoo.api import Environment
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon
from datetime import date, timedelta

import odoo.tests


class TestPointOfSaleHttpCommon(AccountTestInvoicingHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        env = cls.env
        cls.env.user.groups_id += env.ref('point_of_sale.group_pos_manager')
        journal_obj = env['account.journal']
        account_obj = env['account.account']
        main_company = cls.company_data['company']

        account_receivable = account_obj.create({'code': 'X1012',
                                                 'name': 'Account Receivable - Test',
                                                 'user_type_id': env.ref('account.data_account_type_receivable').id,
                                                 'reconcile': True})
        env.company.account_default_pos_receivable_account_id = account_receivable
        env['ir.property']._set_default('property_account_receivable_id', 'res.partner', account_receivable, main_company)
        # Pricelists are set below, do not take demo data into account
        env['ir.property'].sudo().search([('name', '=', 'property_product_pricelist')]).unlink()

        cls.bank_journal = journal_obj.create({
            'name': 'Bank Test',
            'type': 'bank',
            'company_id': main_company.id,
            'code': 'BNK',
            'sequence': 10,
        })

        env['pos.payment.method'].create({
            'name': 'Bank',
            'journal_id': cls.bank_journal.id,
        })
        cls.main_pos_config = env['pos.config'].create({
            'name': 'Shop',
            'barcode_nomenclature_id': env.ref('barcodes.default_barcode_nomenclature').id,
            'iface_orderline_customer_notes': True,
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

        # Archive all existing product to avoid noise during the tours
        all_pos_product = env['product.product'].search([('available_in_pos', '=', True)])
        discount = env.ref('point_of_sale.product_product_consumable')
        cls.tip = env.ref('point_of_sale.product_product_tip')
        (all_pos_product - discount - cls.tip)._write({'active': False})

        # In DESKS categ: Desk Pad
        pos_categ_desks = env.ref('point_of_sale.pos_category_desks')

        # In DESKS categ: Whiteboard Pen
        pos_categ_misc = env.ref('point_of_sale.pos_category_miscellaneous')

        # In CHAIR categ: Letter Tray
        pos_categ_chairs = env.ref('point_of_sale.pos_category_chairs')

        # test an extra price on an attribute
        cls.whiteboard_pen = env['product.product'].create({
            'name': 'Whiteboard Pen',
            'available_in_pos': True,
            'list_price': 1.20,
            'taxes_id': False,
            'weight': 0.01,
            'to_weight': True,
            'pos_categ_id': pos_categ_misc.id,
        })
        cls.wall_shelf = env['product.product'].create({
            'name': 'Wall Shelf Unit',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
        })
        cls.small_shelf = env['product.product'].create({
            'name': 'Small Shelf',
            'available_in_pos': True,
            'list_price': 2.83,
            'taxes_id': False,
        })
        cls.magnetic_board = env['product.product'].create({
            'name': 'Magnetic Board',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
        })
        cls.monitor_stand = env['product.product'].create({
            'name': 'Monitor Stand',
            'available_in_pos': True,
            'list_price': 3.19,
            'taxes_id': False,
        })
        cls.desk_pad = env['product.product'].create({
            'name': 'Desk Pad',
            'available_in_pos': True,
            'list_price': 1.98,
            'taxes_id': False,
            'pos_categ_id': pos_categ_desks.id,
        })
        cls.letter_tray = env['product.product'].create({
            'name': 'Letter Tray',
            'available_in_pos': True,
            'list_price': 4.80,
            'taxes_id': False,
            'pos_categ_id': pos_categ_chairs.id,
        })
        cls.desk_organizer = env['product.product'].create({
            'name': 'Desk Organizer',
            'available_in_pos': True,
            'list_price': 5.10,
            'taxes_id': False,
        })
        configurable_chair = env['product.product'].create({
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
            'product_tmpl_id': cls.whiteboard_pen.product_tmpl_id.id,
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
            'product_tmpl_id': configurable_chair.product_tmpl_id.id,
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
        chair_legs_line = env['product.template.attribute.line'].create({
            'product_tmpl_id': configurable_chair.product_tmpl_id.id,
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
        chair_fabrics_other = env['product.attribute.value'].create({
            'name': 'Other',
            'attribute_id': chair_fabrics_attribute.id,
            'is_custom': True,
        })
        chair_fabrics_line = env['product.template.attribute.line'].create({
            'product_tmpl_id': configurable_chair.product_tmpl_id.id,
            'attribute_id': chair_fabrics_attribute.id,
            'value_ids': [(6, 0, [chair_fabrics_leather.id, chair_fabrics_other.id])]
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
                'product_id': cls.wall_shelf.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 13.95,  # test for issues like in 7f260ab517ebde634fc274e928eb062463f0d88f
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.id,
            })],
        })

        env['product.pricelist'].create({
            'name': 'Percentage',
            'item_ids': [(0, 0, {
                'compute_price': 'percentage',
                'percent_price': 100,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.id,
            }), (0, 0, {
                'compute_price': 'percentage',
                'percent_price': 99,
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.id,
            }), (0, 0, {
                'compute_price': 'percentage',
                'percent_price': 0,
                'applied_on': '0_product_variant',
                'product_id': cls.magnetic_board.id,
            })],
        })

        env['product.pricelist'].create({
            'name': 'Formula',
            'item_ids': [(0, 0, {
                'compute_price': 'formula',
                'price_discount': 6,
                'price_surcharge': 5,
                'applied_on': '0_product_variant',
                'product_id': cls.wall_shelf.id,
            }), (0, 0, {
                # .99 prices
                'compute_price': 'formula',
                'price_surcharge': -0.01,
                'price_round': 1,
                'applied_on': '0_product_variant',
                'product_id': cls.small_shelf.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_min_margin': 10,
                'price_max_margin': 100,
                'applied_on': '0_product_variant',
                'product_id': cls.magnetic_board.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_surcharge': 10,
                'price_max_margin': 5,
                'applied_on': '0_product_variant',
                'product_id': cls.monitor_stand.id,
            }), (0, 0, {
                'compute_price': 'formula',
                'price_discount': -100,
                'price_min_margin': 5,
                'price_max_margin': 20,
                'applied_on': '0_product_variant',
                'product_id': cls.desk_pad.id,
            })],
        })

        env['product.pricelist'].create({
            'name': 'min_quantity ordering',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '0_product_variant',
                'min_quantity': 2,
                'product_id': cls.wall_shelf.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '0_product_variant',
                'min_quantity': 1,
                'product_id': cls.wall_shelf.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '0_product_variant',
                'min_quantity': 2,
                'product_id': env.ref('point_of_sale.product_product_consumable').id,
            })],
        })

        env['product.pricelist'].create({
            'name': 'Product template',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '1_product',
                'product_tmpl_id': cls.wall_shelf.product_tmpl_id.id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })

        product_category_3 = env['product.category'].create({
            'name': 'Services',
            'parent_id': env.ref('product.product_category_1').id,
        })

        env['product.pricelist'].create({
            # no category has precedence over category
            'name': 'Category vs no category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': product_category_3.id,  # All / Saleable / Services
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
            })],
        })

        p = env['product.pricelist'].create({
            'name': 'Category',
            'item_ids': [(0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 2,
                'applied_on': '2_product_category',
                'categ_id': env.ref('product.product_category_all').id,
            }), (0, 0, {
                'compute_price': 'fixed',
                'fixed_price': 1,
                'applied_on': '2_product_category',
                'categ_id': product_category_3.id,  # All / Saleable / Services
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

        all_pricelists = env['product.pricelist'].search([('id', '!=', excluded_pricelist.id)])
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
                                            'receivable_account_id': account_receivable.id,
            })],
            'use_pricelist': True,
            'pricelist_id': public_pricelist.id,
            'available_pricelist_ids': [(4, pricelist.id) for pricelist in all_pricelists],
            'module_pos_loyalty': False,
        })

        # Change the default sale pricelist of customers,
        # so the js tests can expect deterministically this pricelist when selecting a customer.
        env['ir.property']._set_default(
            "property_product_pricelist",
            "res.partner",
            public_pricelist,
        )


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    def test_01_pos_basic_order(self):

        self.main_pos_config.write({
            'iface_tipproduct': True,
            'tip_product_id': self.tip.id,
        })

        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.open_session_cb(check_coa=False)

        # needed because tests are run before the module is marked as
        # installed. In js web will only load qweb coming from modules
        # that are returned by the backend in module_boot. Without
        # this you end up with js, css but no qweb.
        self.env['ir.module.module'].search([('name', '=', 'point_of_sale')], limit=1).state = 'installed'

        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_pricelist', login="accountman")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_basic_order', login="accountman")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ProductScreenTour', login="accountman")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenTour', login="accountman")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ReceiptScreenTour', login="accountman")

        for order in self.env['pos.order'].search([]):
            self.assertEqual(order.state, 'paid', "Validated order has payment of " + str(order.amount_paid) + " and total of " + str(order.amount_total))

        # check if email from ReceiptScreenTour is properly sent
        email_count = self.env['mail.mail'].search_count([('email_to', '=', 'test@receiptscreen.com')])
        self.assertEqual(email_count, 1)

    def test_02_pos_with_invoiced(self):
        self.main_pos_config.open_session_cb(check_coa=False)
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ChromeTour', login="accountman")
        n_invoiced = self.env['pos.order'].search_count([('state', '=', 'invoiced')])
        n_paid = self.env['pos.order'].search_count([('state', '=', 'paid')])
        self.assertEqual(n_invoiced, 1, 'There should be 1 invoiced order.')
        self.assertEqual(n_paid, 2, 'There should be 2 paid order.')

    def test_04_product_configurator(self):
        self.main_pos_config.write({ 'product_configurator': True })
        self.main_pos_config.open_session_cb(check_coa=False)
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config, 'ProductConfiguratorTour', login="accountman")

    def test_05_ticket_screen(self):
        self.main_pos_config.open_session_cb(check_coa=False)
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'TicketScreenTour', login="accountman")
