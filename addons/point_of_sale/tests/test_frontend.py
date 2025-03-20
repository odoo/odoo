# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from unittest.mock import patch
from odoo import Command

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleDataHttpCommon):
    def test_pos_pricelist(self):
        self.start_pos_tour('pos_pricelist')

    def test_pos_product_screen(self):
        self.start_pos_tour('ProductScreenTour')

    def test_pos_multi_payment_and_change(self):
        self.start_pos_tour('pos_basic_order_01_multi_payment_and_change')

    def test_basic_order_decimal_qty(self):
        self.start_pos_tour('pos_basic_order_02_decimal_order_quantity')

    def test_pos_basic_order_tax_position(self):
        self.start_pos_tour('pos_basic_order_03_tax_position')

    def test_pos_floating_order(self):
        self.start_pos_tour('FloatingOrderTour')

    def test_pos_payment_screen(self):
        self.start_pos_tour('PaymentScreenTour')

    def test_pos_receipt_screen(self):
        self.start_pos_tour('ReceiptScreenTour')        # check if email from ReceiptScreenTour is properly sent
        email_count = self.env['mail.mail'].search_count([('email_to', '=', 'test@receiptscreen.com')])
        self.assertEqual(email_count, 1)

    def test_pos_with_invoiced(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })

        self.start_pos_tour('ChromeTour')
        n_invoiced = self.env['pos.order'].search_count([('account_move', '!=', False)])
        n_paid = self.env['pos.order'].search_count([('state', '=', 'paid')])
        self.assertEqual(n_invoiced, 1, 'There should be 1 invoiced order.')
        self.assertEqual(n_paid, 2, 'There should be 3 paid order.')
        last_order = self.env['pos.order'].search([], limit=1, order="id desc")
        self.assertEqual(last_order.lines[0].price_subtotal, 30.0)
        self.assertEqual(last_order.lines[0].price_subtotal_incl, 30.0)
        # Check if session name contains config name as prefix
        self.assertEqual(self.pos_config.name in last_order.session_id.name, True)

    def test_product_configurator(self):
        # Making one attribute inactive to verify that it doesn't show
        configurable_product = self.env['product.product'].search([('name', '=', 'Configurable 1'), ('available_in_pos', '=', 'True')], limit=1)
        value_line = configurable_product.attribute_line_ids[2]
        value_line.product_template_value_ids[1].ptav_active = False
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        self.start_pos_tour('ProductConfiguratorTour')

    def test_optional_product(self):
        self.product_pricelist_five.write({'pos_optional_product_ids': [
            Command.set([ self.product_pricelist_two.id ])
        ]})

        self.product_pricelist_six.write({'pos_optional_product_ids': [
            Command.set([ self.product_configurable.id ])
        ]})

        self.start_pos_tour('test_optional_product')

    def test_ticket_screen(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })
        self.start_pos_tour('TicketScreenTour')

    def test_product_information_screen_admin(self):
        self.pos_admin.write({
            'group_ids': [Command.link(self.env.ref('base.group_system').id)],
        })
        self.assertFalse(self.product_awesome_thing.is_storable)
        self.start_pos_tour('CheckProductInformation', login="pos_admin")

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
        self.env['product.product'].create({
            'name': 'Zero Amount Product',
            'available_in_pos': True,
            'list_price': 0,
            'taxes_id': [(6, 0, [fixed_tax.id])],
            'categ_id': self.env.ref('product.product_category_services').id,
        })

        # Make an order with the zero-amount product from the frontend.
        # We need to do this because of the fix in the "compute_all" port.
        self.pos_config.write({'iface_tax_included': 'total'})
        self.start_tour("/pos/ui?config_id=%d" % self.pos_config.id, 'FixedTaxNegativeQty', login="pos_user")
        pos_session = self.pos_config.current_session_id

        # Close the session and check the session journal entry.
        pos_session.action_pos_session_validate()
        lines = pos_session.move_id.line_ids.sorted('balance')

        # order in the tour is paid using the bank payment method.
        bank_pm = self.pos_config.payment_method_ids.filtered(lambda pm: pm.name == 'Bank')
        self.assertEqual(lines[0].account_id, bank_pm.receivable_account_id or self.env.company.account_default_pos_receivable_account_id)
        self.assertAlmostEqual(lines[0].balance, -1)
        self.assertEqual(lines[1].account_id, self.env.company.income_account_id)
        self.assertAlmostEqual(lines[1].balance, 0)
        self.assertEqual(lines[2].account_id, tax_received_account)
        self.assertAlmostEqual(lines[2].balance, 1)

    def test_change_without_cash_method(self):
        self.pos_config.write({'ship_later': True})
        self.start_pos_tour('PaymentScreenTour2')

    def test_pos_closing_cash_details(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        current_session.post_closing_cash_details(0)
        current_session.close_session_from_ui()
        self.start_pos_tour('CashClosingDetails')
        cash_diff_line = self.env['account.bank.statement.line'].search([
            ('payment_ref', 'ilike', 'Cash difference observed during the counting (Loss)')
        ])
        self.assertAlmostEqual(cash_diff_line.amount, -1.00)

    def test_cash_payments_should_reflect_on_next_opening(self):
        self.start_pos_tour('OrderPaidInCash')

    def test_fiscal_position_no_tax(self):
        self.start_pos_tour('FiscalPositionNoTax')

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
        self.product_awesome_item.write({
            'taxes_id': [(6, 0, [tax_inclusive_1.id])],
            'list_price': 100,
        })
        self.product_awesome_article.write({
            'taxes_id': [(6, 0, [tax_exclusive_1.id])],
            'list_price': 100,
        })
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
        self.pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [
                    fiscal_position_1.id,
                    fiscal_position_2.id,
                    fiscal_position_3.id,
                    fiscal_position_4.id,
                ])],
        })
        self.start_pos_tour('FiscalPositionIncl')
        self.start_pos_tour('FiscalPositionExcl')

    def test_product_combo(self):
        setup_product_combo_items(self)
        self.office_combo.write({'lst_price': 50})
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

    def test_pos_barcodes_scan(self):
        barcode_rule = self.env.ref("point_of_sale.barcode_rule_client")
        barcode_rule.pattern = barcode_rule.pattern + "|234"
        # should in theory be changed in the JS code to `|^234`
        # If not, it will fail as it will mistakenly match with the product barcode "0123456789"
        self.start_pos_tour('BarcodeScanningTour')

    def test_show_tax_excluded(self):
        self.pos_config.write({
            'iface_tax_included': 'subtotal'
        })
        self.start_pos_tour('ShowTaxExcludedTour')

    def test_chrome_without_cash_move_permission(self):
        self.env.user.write({'group_ids': [
            Command.set(
                [
                    self.env.ref('base.group_user').id,
                    self.env.ref('point_of_sale.group_pos_user').id,
                ]
            )
        ]})
        self.start_pos_tour('chrome_without_cash_move_permission', login="accountman")

    def test_pos_barcodes_scan_product_packaging(self):
        pack_of_10 = self.env['uom.uom'].create({
            'name': 'Pack of 10',
            'relative_factor': 10,
            'relative_uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_pos_groupable': True,
        })
        self.product_quality_thing.write({
            'uom_ids': [Command.link(pack_of_10.id)],
            'list_price': 10,
            'taxes_id': False,
            'barcode': '19971997',
        })
        product_product = self.product_quality_thing.product_variant_ids[0]
        self.env['product.uom'].create({
            'barcode': '19981998',
            'product_id': product_product.id,
            'uom_id': pack_of_10.id,
        })
        self.start_pos_tour('BarcodeScanningProductPackagingTour')

    def test_GS1_pos_barcodes_scan(self):
        barcodes_gs1_nomenclature = self.env.ref("barcodes_gs1_nomenclature.default_gs1_nomenclature")
        default_nomenclature_id = self.env.ref("barcodes.default_barcode_nomenclature")
        self.pos_config.company_id.write({
            'nomenclature_id': barcodes_gs1_nomenclature.id
        })
        self.pos_config.write({
            'fallback_nomenclature_id': default_nomenclature_id
        })
        self.product_awesome_article.write({
            'barcode': '08431673020125',
        })
        self.product_awesome_item.write({
            'barcode': '08431673020126',
        })
        # 3760171283370 can be parsed with GS1 rules but it's not GS1
        self.product_awesome_thing.write({
            'barcode': '3760171283370',
        })
        self.start_pos_tour('GS1BarcodeScanningTour')

    def test_refund_order_with_fp_tax_included(self):
        no_tax = self.env['account.tax'].create({'name': "NOT", 'amount': 0})
        self.fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'No Tax',
            'tax_ids': [(0, 0, {
                'tax_src_id': self.tax_15_include.id,
                'tax_dest_id': no_tax.id,
            })],
        })
        self.pos_config.write({
            'fiscal_position_ids': [(4, self.fiscal_position.id)],
            'tax_regime_selection': True,
        })
        self.start_pos_tour('FiscalPositionNoTaxRefund')

    def test_lot_refund(self):
        self.product_awesome_article.write({
            'tracking': 'serial',
        })
        self.start_pos_tour('LotRefundTour')

    def test_receipt_tracking_method(self):
        self.product_awesome_article.write({
            'is_storable': True,
            'tracking': 'lot',
        })
        self.start_pos_tour('ReceiptTrackingMethodTour')

    def test_limited_product_pricelist_loading(self):
        self.env['ir.config_parameter'].sudo().set_param('point_of_sale.limited_product_count', '1')
        limited_category = self.env['pos.category'].create({
            'name': 'Limited Category',
        })
        self.product_pricelist_one.write({
            'pos_categ_ids': [(4, limited_category.id)],
            'list_price': 100,
            'barcode': '0100100',
        })
        self.product_configurable.write({
            'pos_categ_ids': [(4, limited_category.id)],
            'list_price': 200,
        })
        self.product_pricelist_two.write({
            'pos_categ_ids': [(4, limited_category.id)],
            'list_price': 300,
            'barcode': '0100300',
        })

        # Check that two product variant are created
        self.assertEqual(self.product_configurable.product_variant_count, 2)
        self.product_configurable.product_variant_ids[0].write({'barcode': '0100201'})
        self.product_configurable.product_variant_ids[1].write({'barcode': '0100202'})

        pricelist_item = self.env['product.pricelist.item'].create([{
            'applied_on': '3_global',
            'fixed_price': 50,
        }, {
            'applied_on': '1_product',
            'product_tmpl_id': self.product_pricelist_two.id,
            'fixed_price': 100,
        }, {
            'applied_on': '0_product_variant',
            'product_id': self.product_pricelist_one.product_variant_ids[0].id,
            'fixed_price': 80,
        }, {
            'applied_on': '0_product_variant',
            'product_id': self.product_configurable.product_variant_ids[1].id,
            'fixed_price': 120,
        }])
        self.pos_config.write({
            'iface_available_categ_ids': [],
            'limit_categories': True,
        })
        self.pos_config.pricelist_id.write({'item_ids': [(6, 0, pricelist_item.ids)]})
        self.start_pos_tour('limitedProductPricelistLoading')

    def test_multi_product_options(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_manager').id),
            ]
        })
        self.start_pos_tour('MultiProductOptionsTour')

    def test_translate_product_name(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.pos_user.write({'lang': 'fr_FR'})
        self.product_awesome_item.update_field_translations('name', {'fr_FR': 'Magnifique Produit'})
        self.start_pos_tour('TranslateProductNameTour')

    def test_properly_display_price(self):
        lang = self.env['res.lang'].search([('code', '=', self.pos_user.lang)])
        lang.write({'thousands_sep': '.', 'decimal_point': ','})
        self.product_awesome_item.write({'list_price': 1453.53})
        self.start_pos_tour('DecimalCommaOrderlinePrice')

    def test_res_partner_scan_barcode(self):
        self.start_pos_tour('BarcodeScanPartnerTour')

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
                self.start_pos_tour('OrderModificationAfterValidationError')

            warning_outputs = [o for o in log_catcher.output if 'WARNING' in o]
            self.assertEqual(len(warning_outputs), 1, "Exactly one warning should be logged")

    def test_customer_display(self):
        self.start_tour(f"/pos_customer_display/{self.pos_config.id}/{self.pos_config.access_token}", 'CustomerDisplayTour', login="pos_user")

    def test_refund_few_quantities(self):
        """ Test to check that refund works with quantities of less than 0.5 """
        self.product_awesome_article.write({
            'list_price': 3,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
        })
        self.start_pos_tour('RefundFewQuantities')

    def test_customer_display_as_public(self):
        self.pos_config.customer_display_type = 'remote'
        self.pos_config.customer_display_bg_img = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        response = self.url_open(f"/web/image/pos.config/{self.pos_config.id}/customer_display_bg_img")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Shop.png' in response.headers['Content-Disposition'])

    def test_customer_all_fields_displayed(self):
        """
        Verify that all the field of a partner can be displayed in the partner list.
        Also verify that all these fields can be searched.
        """
        self.start_pos_tour('PosCustomerAllFieldsDisplayed')

    def test_product_combo_change_fp(self):
        """
        Verify than when the fiscal position is changed,
        the price of the combo doesn't change and taxes are well taken into account
        """
        setup_product_combo_items(self)
        self.source_tax.write({'price_include_override': 'tax_included'})
        self.destination_tax.write({'price_include_override': 'tax_included'})
        self.office_combo.write({'list_price': 50, 'taxes_id': [(6, 0, [self.source_tax.id])]})
        self.office_combo.combo_ids.combo_item_ids.product_id.write({'taxes_id': [(6, 0, [self.source_tax.id])]})
        self.start_pos_tour('ProductComboChangeFP')

    def test_cash_rounding_payment(self):
        """Verify than an error popup is shown if the payment value is more precise than the rounding method"""
        self.env['ir.config_parameter'].sudo().set_param('barcode.max_time_between_keys_in_ms', 1)
        rounding_method = self.env['account.cash.rounding'].create({
            'name': 'Down 0.10',
            'rounding': 0.10,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company_data['default_account_revenue'].copy().id,
            'loss_account_id': self.company_data['default_account_expense'].copy().id,
            'rounding_method': 'DOWN',
        })
        self.pos_config.write({
            'cash_rounding': True,
            'only_round_cash_method': False,
            'rounding_method': rounding_method.id,
        })
        self.start_pos_tour('CashRoundingPayment', login="accountman")

    def test_product_categories_order(self):
        self.start_pos_tour('PosCategoriesOrder')

    def test_product_with_dynamic_attributes(self):
        self.start_pos_tour("PosProductWithDynamicAttributes")

    def test_lot(self):
        self.product_awesome_article.write({
            'tracking': 'serial',
        })
        self.start_pos_tour('LotTour')

    def test_product_search(self):
        self.start_pos_tour('ProductSearchTour')

    def test_sort_orderlines_by_product_categoryies(self):
        """ Test to ensure orderlines are added to the cart in the correct order based on their categories"""
        self.pos_config.write({'orderlines_sequence_in_cart_by_category': True})
        self.start_pos_tour('SortOrderlinesByCategories')

    def test_customer_popup(self):
        """Verify that the customer popup search & inifnite scroll work properly"""
        self.env["res.partner"].create([{"name": "Z partner to search"}, {"name": "Z partner to scroll"}])
        self.start_pos_tour('CustomerPopupTour')

    def test_pricelist_multi_items_different_qty_thresholds(self):
        """ Having multiple pricelist items for the same product tmpl with ascending `min_quantity`
        values, prefer the "latest available"- that is, the one with greater `min_quantity`.
        """
        self.pos_config.pricelist_id.write({
            'item_ids': [Command.create({
                'display_applied_on': '1_product',
                'product_tmpl_id': self.product_awesome_item.id,
                'compute_price': 'fixed',
                'fixed_price': 10.0,
                'min_quantity': 3,
            }), Command.create({
                'display_applied_on': '1_product',
                'product_tmpl_id': self.product_awesome_item.id,
                'compute_price': 'fixed',
                'fixed_price': 20.0,
                'min_quantity': 2,
            })],
        })
        self.start_pos_tour('test_pricelist_multi_items_different_qty_thresholds')

    def test_tracking_number_closing_session(self):
        self.start_pos_tour('test_tracking_number_closing_session')
        for order in self.env['pos.order'].search([]):
            self.assertEqual(int(order.tracking_number) % 100, 1)

    def test_reload_page_before_payment_with_customer_account(self):
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.pos_config.write({'payment_method_ids': [(6, 0, self.customer_account_payment_method.ids)]})
        self.start_pos_tour('test_reload_page_before_payment_with_customer_account')

    def test_product_card_qty_precision(self):
        self.start_pos_tour('ProductCardUoMPrecision')


# This class just runs the same tests as above but with mobile emulation
class MobileTestUi(TestUi):
    browser_size = '375x667'
    touch_enabled = True
    allow_inherited_tests_method = True
