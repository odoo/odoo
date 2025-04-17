# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch
from odoo import Command

from odoo.tests import tagged
from odoo.addons.account.tests.common import TestTaxCommon
from odoo.addons.point_of_sale.tests.common_data_setup import setup_test_pos
from odoo.addons.account.tests.common import AccountTestInvoicingHttpCommon

from odoo.exceptions import UserError


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
        cls.main_company = cls._get_main_company()
        cls.company_data_2 = cls.setup_other_company()
        setup_test_pos(cls)



@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    def test_01_pos_basic_order(self):
        # Mark a product as favorite to check if it is displayed in first position
        self.whiteboard_pen.write({
            'is_favorite': True
        })

        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.with_user(self.pos_user).open_ui()

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
            'group_ids': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ChromeTour', login="pos_user")
        n_invoiced = self.env['pos.order'].search_count([('account_move', '!=', False)])
        n_paid = self.env['pos.order'].search_count([('state', '=', 'paid')])
        self.assertEqual(n_invoiced, 1, 'There should be 1 invoiced order.')
        self.assertEqual(n_paid, 2, 'There should be 3 paid order.')
        last_order = self.env['pos.order'].search([], limit=1, order="id desc")
        self.assertEqual(last_order.lines[0].price_subtotal, 30.0)
        self.assertEqual(last_order.lines[0].price_subtotal_incl, 30.0)
        # Check if session name contains config name as prefix
        self.assertEqual(self.main_pos_config.name in last_order.session_id.name, True)

    def test_04_product_configurator(self):
        # Making one attribute inactive to verify that it doesn't show
        fabrics_line = self.configurable_chair.attribute_line_ids[2]
        fabrics_line.product_template_value_ids[1].ptav_active = False  # Wool - inactive
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('ProductConfiguratorTour')

    def test_optional_product(self):
        # optional product in pos
        self.desk_pad.write({'pos_optional_product_ids': [
            Command.set([self.small_shelf.id])
        ]})
        self.letter_tray.write({'pos_optional_product_ids': [
            Command.set([self.configurable_chair.id])
        ]})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_optional_product')

    def test_05_ticket_screen(self):
        self.pos_user.write({
            'group_ids': [
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
            'group_ids': [Command.link(self.env.ref('base.group_system').id)],
        })
        self.assertFalse(self.product_a.is_storable)
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'CheckProductInformation', login="pos_admin")

    def test_fixed_tax_negative_qty(self):
        """ Assert the negative amount of a negative-quantity orderline
            with zero-amount product with fixed tax.
        """

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
        # setup the zero-amount product
        self.letter_tray.write({
            'list_price': 0,
            'taxes_id': [(6, 0, [fixed_tax.id])],
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
        bank_pm = self.bank_payment_method

        self.assertEqual(lines[0].account_id, bank_pm.receivable_account_id or self.env.company.account_default_pos_receivable_account_id)
        self.assertAlmostEqual(lines[0].balance, -1)
        self.assertEqual(lines[1].account_id, self.env.company.income_account_id)
        self.assertAlmostEqual(lines[1].balance, 0)
        self.assertEqual(lines[2].account_id, tax_received_account)
        self.assertAlmostEqual(lines[2].balance, 1)

    def test_change_without_cash_method(self):
        # there should be only bank payment method
        self.main_pos_config.payment_method_ids = self.bank_payment_method.ids
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenTour2', login="pos_user")

    def test_rounding_up(self):
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding up',
            'rounding': 0.05,
            'rounding_method': 'UP',
        })
        self.desk_organizer.write({
            'list_price': 1.96,
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
        self.desk_organizer.write({
            'list_price': 1.98,
            'taxes_id': False,
        })
        self.main_pos_config.write({
            'rounding_method': rouding_method.id,
            'cash_rounding': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenRoundingDown', login="pos_user")
        self.env["pos.order"].search([]).write({'state': 'cancel'})
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenTotalDueWithOverPayment', login="pos_user")

    def test_rounding_half_up(self):
        rouding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding HALF-UP',
            'rounding': 0.5,
            'rounding_method': 'HALF-UP',
        })

        self.env['product.product'].create({
            'name': 'Product Test 1.20',
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
        # create a fiscal position that map the tax to no tax
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'No Tax',
            'tax_ids': [(0, 0, {
                'tax_src_id': self.account_tax_10_incl.id,
                'tax_dest_id': False,
            })],
        })
        self.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [fiscal_position.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionNoTax', login="pos_user")

    def test_fiscal_position_inclusive_and_exclusive_tax(self):
        """ Test the mapping of fiscal position for both Tax Inclusive ans Tax Exclusive"""
        # create a tax with price included
        self.account_tax_05_excl.write({'amount': 20})
        account_tax_10_excl = self.env['account.tax'].create({
            'name': 'Tax excl.10%',
            'amount': 10,
            'price_include_override': 'tax_excluded',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })

        self.letter_tray.write({
            'list_price': 100,
            'taxes_id': [(6, 0, [self.tax20in.id])],
        })
        self.desk_organizer.write({
            'list_price': 100,
            'taxes_id': [(6, 0, [self.account_tax_05_excl.id])],
        })

        # create a fiscal position that map the tax
        fiscal_positions = self.env['account.fiscal.position'].create([
            {
                'name': 'Incl. to Incl.',
                'tax_ids': [(0, 0, {
                    'tax_src_id': self.tax20in.id,
                    'tax_dest_id': self.account_tax_10_incl.id,
                })],
            }, {
                'name': 'Incl. to Excl.',
                'tax_ids': [(0, 0, {
                    'tax_src_id': self.tax20in.id,
                    'tax_dest_id': account_tax_10_excl.id,
                })],
            }, {
                'name': 'Excl. to Excl.',
                'tax_ids': [(0, 0, {
                    'tax_src_id': self.account_tax_05_excl.id,
                    'tax_dest_id': account_tax_10_excl.id,
                })],
            }, {
                'name': 'Excl. to Incl.',
                'tax_ids': [(0, 0, {
                    'tax_src_id': self.account_tax_05_excl.id,
                    'tax_dest_id': self.account_tax_10_incl.id,
                })],
            }
        ])

        # add the fiscal position to the PoS
        self.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, fiscal_positions.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionIncl', login="pos_user")
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionExcl', login="pos_user")

    def test_06_pos_discount_display_with_multiple_pricelist(self):
        """ Test the discount display on the POS screen when multiple pricelists are used."""
        self.desk_organizer.write({
            'list_price': 10,
        })
        self.env['product.pricelist.item'].create({
            'pricelist_id': self.public_pricelist.id,
            'product_tmpl_id': self.desk_organizer.id,
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
            'base_pricelist_id': self.public_pricelist.id,
            'compute_price': 'percentage',
            'applied_on': '3_global',
            'percent_price': 10,
        })
        self.main_pos_config.write({
            'pricelist_id': self.public_pricelist.id,
            'available_pricelist_ids': [(6, 0, [self.public_pricelist.id, special_pricelist.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ReceiptScreenDiscountWithPricelistTour', login="pos_user")

    def test_product_combo(self):
        # Add configurable product to the combo
        self.chairs_combo.write({
            'combo_item_ids': [Command.create({'product_id': self.configurable_chair.product_variant_id.id})]
        })
        self.office_combo.write({
            'lst_price': 50,
            'barcode': 'SuperCombo',
        })
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

    def test_product_combo_max_free_qty(self):
        """ Test the max free quantity of a product combo."""
        self.desks_combo.write({
            'qty_free': 2,
            'qty_max': 2,
        })
        self.chairs_combo.write({
            'qty_free': 2,
            'qty_max': 5,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('ProductComboMaxFreeQtyTour')

    def test_07_pos_barcodes_scan(self):
        barcode_rule = self.env.ref("point_of_sale.barcode_rule_client")
        barcode_rule.pattern = barcode_rule.pattern + "|234"
        # should in theory be changed in the JS code to `|^234`
        # If not, it will fail as it will mistakenly match with the product barcode "0123456789"

        # merge test_09_pos_barcodes_scan_product_packaging
        pack_of_10 = self.env['uom.uom'].create({
            'name': 'Pack of 10',
            'relative_factor': 10,
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_pos_groupable': True,
        })
        self.monitor_stand.write({'uom_ids': [Command.link(pack_of_10.id)]})
        self.env['product.uom'].create({
            'barcode': '12345610',
            'product_id': self.monitor_stand.product_variant_id.id,
            'uom_id': pack_of_10.id,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'BarcodeScanningTour', login="pos_user")

    def test_08_show_tax_excluded(self):
        self.test_product3.write({
            'list_price': 110,
        })

        # set Tax-Excluded Price
        self.main_pos_config.write({
            'iface_tax_included': 'subtotal'
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'ShowTaxExcludedTour', login="pos_user")

    def test_chrome_without_cash_move_permission(self):
        self.env.user.write({'group_ids': [
            Command.set(
                [
                    self.env.ref('base.group_user').id,
                    self.env.ref('point_of_sale.group_pos_user').id,
                ]
            )
        ]})
        self.main_pos_config.open_ui()
        self.start_pos_tour('chrome_without_cash_move_permission', login="accountman")

    def test_GS1_pos_barcodes_scan(self):
        barcodes_gs1_nomenclature = self.env.ref("barcodes_gs1_nomenclature.default_gs1_nomenclature")
        default_nomenclature_id = self.env.ref("barcodes.default_barcode_nomenclature")
        self.main_pos_config.company_id.write({
            'nomenclature_id': barcodes_gs1_nomenclature.id
        })
        self.main_pos_config.write({
            'fallback_nomenclature_id': default_nomenclature_id
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
        zero_tax = self.env['account.tax'].create({
            'name': 'Tax 2',
            'amount': 0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'price_include_override': 'tax_included',
        })
        # fiscal position with the two taxes
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'No Tax',
            'tax_ids': [(0, 0, {
                'tax_src_id': self.account_tax_10_incl.id,
                'tax_dest_id': zero_tax.id,
            })],
        })
        # add the fiscal position to the PoS
        self.main_pos_config.write({
            'fiscal_position_ids': [(4, fiscal_position.id)],
            'tax_regime_selection': True,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'FiscalPositionNoTaxRefund', login="pos_user")

    def test_lot_refund(self):
        self.test_product3.write({'tracking': 'serial'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'LotRefundTour', login="pos_user")

    def test_printed_receipt_tour(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour("point_of_sale.test_printed_receipt_tour")

    def test_limited_product_pricelist_loading(self):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', '1')
        self.test_product4.write({
            'barcode': '0100100',
            'taxes_id': False,
            'pos_categ_ids': [(4, self.pos_cat_desk_test.id)],
        })
        self.test_product3.write({
            'barcode': '0100300',
            'taxes_id': False,
            'pos_categ_ids': [(4, self.pos_cat_desk_test.id)],
        })

        self.desk_organizer.write({
            'list_price': 200,
            'pos_categ_ids': [(4, self.pos_cat_desk_test.id)],
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.always_color_attribute.id,
                'value_ids': [(6, 0, self.always_color_attribute.value_ids.ids)]
            })],
        })
        # Check that two product variant are created
        self.assertEqual(self.desk_organizer.product_variant_count, 2)
        self.desk_organizer.product_variant_ids[0].write({'barcode': '0100201'})
        self.desk_organizer.product_variant_ids[1].write({'barcode': '0100202'})

        pricelist_item = self.env['product.pricelist.item'].create([{
            'applied_on': '3_global',
            'fixed_price': 50,
        }, {
            'applied_on': '1_product',
            'product_tmpl_id': self.desk_organizer.id,
            'fixed_price': 100,
        }, {
            'applied_on': '0_product_variant',
            'product_id': self.test_product4.id,
            'fixed_price': 80,
        }, {
            'applied_on': '0_product_variant',
            'product_id': self.desk_organizer.product_variant_ids[1].id,
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
            'group_ids': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        multi_attribute = self.env['product.attribute'].create({
            'name': 'Multi',
            'display_type': 'multi',
            'create_variant': 'no_variant',
            'value_ids': [
                (0, 0, {'name': 'Value 1'}),
                (0, 0, {'name': 'Value 2'}),
            ]
        })
        self.desk_organizer.write({
            'list_price': 10,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': multi_attribute.id,
                'value_ids': [(6, 0, multi_attribute.value_ids.ids)]
            })],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'MultiProductOptionsTour', login="pos_user")

    def test_translate_product_name(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.pos_user.write({'lang': 'fr_FR'})
        self.test_product3.update_field_translations('name', {'fr_FR': 'Testez le produit 3'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'TranslateProductNameTour', login="pos_user")

    def test_properly_display_price(self):
        """Make sure that when the decimal separator is a comma, the shown orderline price is correct.
        """
        lang = self.env['res.lang'].search([('code', '=', self.pos_user.lang)])
        lang.write({'thousands_sep': '.', 'decimal_point': ','})
        self.test_product3.write({'list_price': 1_453.53})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, "DecimalCommaOrderlinePrice", login="pos_user")

    def test_res_partner_scan_barcode(self):
        # default Customer Barcodes pattern is '042'
        self.partner1.write({'barcode': '0421234567890'})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'BarcodeScanPartnerTour', login="pos_user")

    def test_allow_order_modification_after_validation_error(self):
        """
        User error as a result of validation should block the order.
        Taking action by order modification should be allowed.
        """
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
        self.test_product3.write({
            'list_price': 3,
            'taxes_id': False,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'RefundFewQuantities', login="pos_user")

    def test_product_combo_price(self):
        """ Check that the combo has the expected price """
        # all combo have one product init
        self.desks_combo.write({'combo_item_ids': [Command.unlink(item.id) for item in self.desks_combo.combo_item_ids[1:]]})
        self.chairs_combo.write({'combo_item_ids': [Command.unlink(item.id) for item in self.chairs_combo.combo_item_ids[1:]]})
        self.desk_accessories_combo.write({'combo_item_ids': [Command.unlink(item.id) for item in self.desk_accessories_combo.combo_item_ids[1:]]})

        self.desks_combo.combo_item_ids[0].product_id.write({"lst_price": 7, "taxes_id": False})
        self.chairs_combo.combo_item_ids[0].product_id.write({"lst_price": 2.5, "taxes_id": False})
        self.desk_accessories_combo.combo_item_ids[0].product_id.write({"lst_price": 1.5, "taxes_id": False})

        self.office_combo.write({
            "list_price": 7,
            "standard_price": 10,
            "taxes_id": False,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'ProductComboPriceCheckTour', login="pos_user")
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.type == 'combo').margin, 0)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.type == 'combo').margin_percent, 0)

    def test_customer_display_as_public(self):
        self.main_pos_config.customer_display_bg_img = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        response = self.url_open(f"/web/image/pos.config/{self.main_pos_config.id}/customer_display_bg_img")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Shop.png' in response.headers['Content-Disposition'])

    def test_customer_all_fields_displayed(self):
        """
        Verify that all the field of a partner can be displayed in the partner list.
        Also verify that all these fields can be searched.
        """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PosCustomerAllFieldsDisplayed')

    def test_product_combo_change_fp(self):
        """
        Verify than when the fiscal position is changed,
        the price of the combo doesn't change and taxes are well taken into account
        """
        self.office_combo.write({'list_price': 50, 'taxes_id': [(6, 0, [self.tax20in.id])]})
        for combo in self.office_combo.combo_ids:  # Set the tax to all the products of the combo
            for item in combo.combo_item_ids:
                item.product_id.taxes_id = [(6, 0, [self.tax20in.id])]

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'test fp',
            'tax_ids': [(0, 0, {
                'tax_src_id': self.tax20in.id,
                'tax_dest_id': self.account_tax_10_incl.id,
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
        aaa_catg = self.env['pos.category'].create({
            'name': 'AAA',
            'parent_id': False,
            'sequence': 1,
        })
        aac_catg = self.env['pos.category'].create({
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
        aay_catg = self.env['pos.category'].create({
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
        self.env['product.product'].create([
            {
                'name': 'Product in AAA Catg',
                'pos_categ_ids': [(6, 0, [aaa_catg.id])],
                'available_in_pos': True,
            },
            {
                'name': 'Product in AAC Catg',
                'pos_categ_ids': [(6, 0, [aac_catg.id])],
                'available_in_pos': True,
            },
            {
                'name': 'Product in AAY Catg',
                'pos_categ_ids': [(6, 0, [aay_catg.id])],
                'available_in_pos': True,
            },
        ])
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'PosCategoriesOrder', login="pos_admin")

    def test_product_with_dynamic_attributes(self):
        dynamic_attribute = self.env['product.attribute'].create({
            'name': 'Dynamic Attribute',
            'create_variant': 'dynamic',
            'value_ids': [
                (0, 0, {'name': 'Test 1'}),
                (0, 0, {'name': 'Test 2', 'default_extra_price': 10}),
            ]
        })
        self.desk_organizer.write({
            'attribute_line_ids': [(0, 0, {
                'attribute_id': dynamic_attribute.id,
                'value_ids': [(6, 0, dynamic_attribute.value_ids.ids)]
            })],
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'PosProductWithDynamicAttributes', login="pos_admin")
        # TODO: Check that the product is correctly created in the backend

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

    def test_product_search_2(self):
        self.env['product.product'].create({
            'name': 'Test chair 1',
            'available_in_pos': True,
        })
        self.env['product.product'].create({
            'name': 'Test CHAIR 2',
            'available_in_pos': True,
        })
        self.env['product.product'].create({
            'name': 'Test sofa',
            'available_in_pos': True,
            "default_code": "CHAIR_01",
        })
        self.env['product.product'].create({
            'name': 'clémentine',
            'available_in_pos': True,
        })
        self.main_pos_config.open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'SearchProducts', login="pos_user")

    def test_lot(self):
        # merge test_receipt_tracking_method
        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'serial',
            'available_in_pos': True,
        })
        product2 = self.env['product.product'].create({
            'name': 'Product B',
            'is_storable': True,
            'tracking': 'lot',
            'available_in_pos': True,
        })
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product2.id,
            'inventory_quantity': 1,
            'location_id': self.env.user._get_default_warehouse_id().lot_stock_id.id,
            'lot_id': self.env['stock.lot'].create({'name': '1001', 'product_id': product2.id}).id,
        }).sudo().action_apply_inventory()

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

    def test_customer_popup(self):
        """Verify that the customer popup search & inifnite scroll work properly"""
        self.env["res.partner"].create([{"name": "Z partner to search"}, {"name": "Z partner to scroll"}])
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'CustomerPopupTour', login="pos_user")

    def test_pricelist_multi_items_different_qty_thresholds(self):
        """ Having multiple pricelist items for the same product tmpl with ascending `min_quantity`
        values, prefer the "latest available"- that is, the one with greater `min_quantity`.
        """
        self.main_pos_config.pricelist_id.write({
            'item_ids': [Command.create({
                'display_applied_on': '1_product',
                'product_tmpl_id': self.desk_organizer.id,
                'compute_price': 'fixed',
                'fixed_price': 10.0,
                'min_quantity': 3,
            }), Command.create({
                'display_applied_on': '1_product',
                'product_tmpl_id': self.desk_organizer.id,
                'compute_price': 'fixed',
                'fixed_price': 20.0,
                'min_quantity': 2,
            })],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            f'/pos/ui?config_id={self.main_pos_config.id}',
            'test_pricelist_multi_items_different_qty_thresholds',
            login='pos_user'
        )

    def test_tracking_number_closing_session(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'test_tracking_number_closing_session', login="pos_user")
        for order in self.env['pos.order'].search([]):
            self.assertEqual(int(order.tracking_number) % 100, 1)

    def test_reload_page_before_payment_with_customer_account(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            f'/pos/ui?config_id={self.main_pos_config.id}',
            'test_reload_page_before_payment_with_customer_account',
            login='pos_user'
        )

    def test_product_card_qty_precision(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'ProductCardUoMPrecision', login="pos_user")

    def test_cash_in_out(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_basic').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'test_cash_in_out', login="pos_user")

        self.assertEqual(len(self.main_pos_config.current_session_id.statement_line_ids), 1, "There should be one cash in/out statement line")
        self.assertEqual(self.main_pos_config.current_session_id.statement_line_ids[0].amount, -5, "The cash in/out amount should be -5")

    def test_add_multiple_serials_at_once(self):
        self.test_product3.write({
            'is_storable': True,
            'tracking': 'serial',
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, "AddMultipleSerialsAtOnce", login="pos_user")

    def test_order_and_invoice_amounts(self):
        payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'discount_percentage': 10,
            'discount_days': 10,
            'early_discount': True,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })
        self.partner1.property_payment_term_id = payment_term.id

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PaymentScreenInvoiceOrder', login="pos_user")

        order = self.env['pos.order'].search([('partner_id', '=', self.partner1.id)], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.partner_id, self.partner1)

        invoice = self.env['account.move'].search([('invoice_origin', '=', order.pos_reference)], limit=1)
        self.assertTrue(invoice)
        self.assertFalse(invoice.invoice_payment_term_id)

        self.assertAlmostEqual(order.amount_total, invoice.amount_total, places=2, msg="Order and Invoice amounts do not match.")

    def test_product_create_update_from_frontend(self):
        ''' This test verifies product creation and updates product details from the POS frontend. '''
        self.pos_admin.write({
            'group_ids': [Command.link(self.env.ref('base.group_system').id)],
        })
        self.env['pos.category'].search([('id', '!=', self.pos_cat_chair_test.id)]).write({'sequence': 100})
        self.pos_cat_chair_test.write({'sequence': 1})
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour('/pos/ui?config_id=%d' % self.main_pos_config.id, 'test_product_create_update_from_frontend', login='pos_admin')

        # In the frontend, a product was created during the tour with the following details:
        # - Product name: Test Frontend Product
        # - Barcode: 710535977349
        # - List price: 20.0

        #  Ensure that the original product created in the frontend ('Test Frontend Product') has been edited to ('Test Frontend Product Edited').
        frontend_created_product = self.env['product.product'].search_count([('name', '=', 'Test Frontend Product')])
        frontend_created_product_edited = self.env['product.product'].search([('name', '=', 'Test Frontend Product Edited')])

        self.assertEqual(frontend_created_product, 0)
        self.assertEqual(frontend_created_product_edited.name, 'Test Frontend Product Edited')
        self.assertEqual(frontend_created_product_edited.barcode, '710535977348')
        self.assertEqual(frontend_created_product_edited.list_price, 50.0)

    def test_fiscal_position_tax_group_labels(self):
        tax_1 = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 15,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        tax_1.tax_group_id.pos_receipt_label = 'Tax Group 1'

        tax_2 = self.env['account.tax'].create({
            'name': 'Tax 5%',
            'amount': 5,
            'price_include_override': 'tax_included',
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        tax_2.tax_group_id.pos_receipt_label = 'Tax Group 2'

        self.product = self.env['product.product'].create({
            'name': 'Test Product',
            'taxes_id': [(6, 0, [tax_1.id])],
            'list_price': 100,
            'available_in_pos': True,
        })

        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'Fiscal Position Test',
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
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_fiscal_position_tax_group_labels', login="pos_user")

# This class just runs the same tests as above but with mobile emulation
class MobileTestUi(TestUi):
    browser_size = '375x667'
    touch_enabled = True
    allow_inherited_tests_method = True


class TestTaxCommonPOS(TestPointOfSaleHttpCommon, TestTaxCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.name = "AAAAAA"  # The POS only load the first 100 partners

    def create_base_line_product(self, base_line, **kwargs):
        return self.env['product.product'].create({
            **kwargs,
            'available_in_pos': True,
            'list_price': base_line['price_unit'],
            'taxes_id': [Command.set(base_line['tax_ids'].ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })

    def ensure_products_on_document(self, document, product_prefix):
        for i, base_line in enumerate(document['lines'], start=1):
            base_line['product_id'] = self.create_base_line_product(base_line, name=f'{product_prefix}_{i}')

    def assert_pos_order_totals(self, order, expected_values):
        expected_amounts = {}
        if 'tax_amount_currency' in expected_values:
            expected_amounts['amount_tax'] = expected_values['tax_amount_currency']
        if 'total_amount_currency' in expected_values:
            expected_amounts['amount_total'] = expected_values['total_amount_currency']
        self.assertRecordValues(order, [expected_amounts])

    def assert_pos_orders_and_invoices(self, tour, tests_with_orders):
        if self.main_pos_config.current_session_id:
            self.main_pos_config.current_session_id.post_closing_cash_details(0)
            self.main_pos_config.current_session_id.close_session_from_ui()

        self.start_pos_tour(tour)
        orders = self.env['pos.order'].search([('session_id', '=', self.main_pos_config.current_session_id.id)], limit=len(tests_with_orders))
        for index, (order, (test_code, _document, _soft_checking, _amount_type, _amount, expected_values)) in enumerate(zip(orders, tests_with_orders)):
            with self.subTest(test_code=test_code, index=index):
                self.assert_pos_order_totals(order, expected_values)
                if order.account_move:
                    self.assert_invoice_totals(order.account_move, expected_values)
