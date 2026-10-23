# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from contextlib import contextmanager
from unittest.mock import patch

from freezegun import freeze_time

from odoo import Command, api
from odoo.exceptions import UserError
from odoo.tests import loaded_demo_data, tagged

from odoo.addons.point_of_sale.tests.common import (
    PosHttpCommon,
    TestPoSCommon,
)

# TODO-PARP:
# - Move non-tour tests out of HttpCase classes.
# - Move TestPointOfSaleHttpCommon to common.py.


# TODO-PARP: Remove
from unittest import skip

class TestPointOfSaleHttpCommon(TestPoSCommon, PosHttpCommon):
    """HTTP compatibility base retaining the legacy POS setup and order helpers."""

    _test_user_groups = None  # FIXME list needed groups

    # TODO-PARP: Replace it with open_new_session & close_pos_session
    @contextmanager
    def with_new_session(self, config=None, user=None):
        config = config or self.main_pos_config
        user = user or self.pos_user
        config.with_user(user).open_ui()
        session = config.current_session_id
        yield session
        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        cash_pm = self.main_pos_config._get_cash_payment_method()
        session.close_session_from_ui({
            cash_pm.id: expected_cashbox_amount,
        })


@tagged('post_install', '-at_install')
class TestUi(PosHttpCommon):
    _test_user_groups = None  # FIXME list needed groups

    def test_01_point_of_sale_tour(self):
        self.start_tour('/odoo', 'point_of_sale_tour', login='admin')

    def test_01_pos_basic_order(self):
        self.start_pos_tour('pos_pricelist')

    def test_product_screen_tour(self):
        self.whiteboard_pen.write({
            'is_favorite': True
        })
        self.start_pos_tour('ProductScreenTour')

    def test_payment_screen_tour(self):
        self.start_pos_tour('PaymentScreenTour')

    def test_feedback_screen_tour(self):
        self.main_pos_config.write({
            'iface_tipproduct': True,
        })
        self.start_pos_tour('FeedbackScreenTour')
        for order in self.env['pos.order'].search([]):
            self.assertEqual(order.state, 'paid', "Validated order has payment of " + str(order.amount_paid) + " and total of " + str(order.amount_total))

        with patch.object((self.env.registry['pos.order']), 'order_receipt_generate_image', return_value=b'Receipt'):
            order = self.env['pos.order'].search([('amount_total', '=', 72.0)])
            order.action_send_receipt('test1@example.com')
            message = self.env['mail.message'].search([('model', '=', 'pos.order'), ('res_id', '=', order.id)], limit=1)
            self.assertEqual(len(message.attachment_ids), 1, "Should have 1 attachment when basic receipt is False")

            message.unlink()

            self.main_pos_config.basic_receipt = True
            order.action_send_receipt('test2@example.com')
            message = self.env['mail.message'].search([('model', '=', 'pos.order'), ('res_id', '=', order.id)], limit=1)
            self.assertEqual(len(message.attachment_ids), 2, "Should have 2 attachments when basic receipt is True")

    @skip('Temporary to fast merge new valuation')
    def test_02_pos_with_invoiced(self):
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'ChromeTour', login="pos_user")
        n_invoiced = self.env['pos.order'].search_count([('account_move', '!=', False)])
        n_paid = self.env['pos.order'].search_count([('state', '=', 'paid')])
        self.assertEqual(n_invoiced, 1, 'There should be 1 invoiced order.')
        self.assertEqual(n_paid, 2, 'There should be 2 paid order.')
        last_order = self.env['pos.order'].search([], limit=1, order="id desc")
        self.assertEqual(last_order.lines[0].price_subtotal, 30.0)
        self.assertEqual(last_order.lines[0].price_subtotal_incl, 30.0)
        # Check if session name contains config name as prefix
        self.assertEqual(self.main_pos_config.name in last_order.session_id.name, True)

    @skip('Temporary to fast merge new valuation')
    def test_05_ticket_screen(self):
        self.env['res.lang']._lang_get(self.pos_user.lang).write({'date_format': '%m.%d.%Y', 'time_format': '%I.%M.%S %p'})
        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('account.group_account_invoice').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'TicketScreenTour', login="pos_user")
        self.env['res.lang']._lang_get(self.pos_user.lang).write({'date_format': 'MM/dd/yyyy', 'time_format': 'HH:mm:ss'})

    def test_06_tip_screen(self):
        self.main_pos_config.write({'set_tip_after_payment': True, 'iface_tipproduct': True})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'PosTipAfterPaymentTour', login="pos_user")

        orders = self.env['pos.order'].search([], limit=11, order="id desc")
        order_tips = [o.tip_amount for o in orders]

        order_tips.sort()
        self.assertEqual(order_tips, [0.0, 0.0, 0.0, 0.0, 0.0, 0.3, 0.8, 1.0, 1.5, 2.0, 10.0])

    def test_ticket_screen_search_suggestions(self):
        """The search field suggestions must stay above the order list, on mobile too."""
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_ticket_screen_search_suggestions')

    def test_product_information_screen_admin(self):
        '''Consider this test method to contain a test tour with miscellaneous tests/checks that require admin access.
        '''
        self.product_a.available_in_pos = True
        self.pos_admin.write({
            'group_ids': [Command.link(self.env.ref('product.group_product_manager').id)],
        })
        self.main_pos_config.write({
            'is_margins_costs_accessible_to_every_user': True,
        })
        self.assertFalse(self.product_a.is_storable)
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'CheckProductInformation', login="pos_admin")

    def test_pos_session_statistics_display(self):
        """Test that POS session statistics are properly displayed in the UI."""
        # For testing `opening_cash` and `paid_orders` in dashboard
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SessionStatisticsDisplay')

        # For testing `draft_orders`
        self.create_pos_order([[self.desk_pad.product_variant_id, 1, 0, {'price_unit': 10}]], state='draft')

        dashboard_statistics = self.main_pos_config.statistics_for_current_session

        self.assertTrue(dashboard_statistics['date']['is_started'])
        self.assertEqual(dashboard_statistics['cash']['raw_opening_cash'], 100.0)
        self.assertEqual(dashboard_statistics['orders']['paid']['amount'], 45.0)
        self.assertEqual(dashboard_statistics['orders']['paid']['count'], 2)
        self.assertEqual(dashboard_statistics['orders']['draft']['amount'], 10.0)
        self.assertEqual(dashboard_statistics['orders']['draft']['count'], 1)

    def test_07_product_combo(self):
        self.env['decimal.precision'].search([('name', '=', 'Product Price')]).digits = 4
        self._setup_combo_product()
        self.monitor_stand.taxes_id = self.taxes['tax10']
        (self.small_shelf | self.desk_pad | self.desk_organizer).taxes_id = self.taxes['tax15_incl']
        self.desk_accessories_combo.sequence = 100
        combo_product_sofa = self.env["product.template"].create(
            {
                "name": "Combo product Sofa",
                "is_storable": True,
                "available_in_pos": True,
                "list_price": 40,
            }
        )
        sofa_size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'display_type': 'radio',
            'create_variant': 'always',
        })
        sofa_color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'display_type': 'radio',
            'create_variant': 'always',
        })
        sofa_size_L = self.env['product.attribute.value'].create({
            'name': 'L',
            'attribute_id': sofa_size_attribute.id,
        })
        sofa_size_M = self.env['product.attribute.value'].create({
            'name': 'M',
            'attribute_id': sofa_size_attribute.id,
        })
        sofa_color_red = self.env['product.attribute.value'].create({
            'name': 'red',
            'attribute_id': sofa_color_attribute.id,
        })
        sofa_color_blue = self.env['product.attribute.value'].create({
            'name': 'blue',
            'attribute_id': sofa_color_attribute.id,
        })

        product_attribute_size = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': combo_product_sofa.id,
            'attribute_id': sofa_size_attribute.id,
            'value_ids': [Command.set([sofa_size_M.id, sofa_size_L.id])],

        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': combo_product_sofa.id,
            'attribute_id': sofa_color_attribute.id,
            'value_ids': [Command.set([sofa_color_red.id, sofa_color_blue.id])],

        })
        product_attribute_size.product_template_value_ids[0].price_extra = 50
        product_attribute_size.product_template_value_ids[1].price_extra = 100
        self.sofa_combo = self.env["product.combo"].create(
            {
                "name": "Chairs Combo",
                "combo_item_ids": [
                    Command.create({
                        "product_id": combo_product_sofa.product_variant_ids[0].id,
                        "extra_price": 5,
                    }),
                    Command.create({
                        "product_id": combo_product_sofa.product_variant_ids[1].id,
                        "extra_price": 10,
                    }),
                ],
            },
        )
        self.sofa_combo = self.env["product.product"].create(
            {
                "available_in_pos": True,
                "list_price": 20,
                "name": "Sofa Combo",
                "type": "combo",
                "uom_id": self.env.ref("uom.product_uom_unit").id,
                "combo_ids": [
                    Command.set([self.sofa_combo.id]),
                ],
            },
        )
        self.office_combo.barcode = 'SuperCombo'

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('ProductComboPriceTaxIncludedTour')
        order = self.env['pos.order'].search([])
        self.assertEqual(len(order.lines), 4, "There should be 4 order lines - 1 combo parent and 3 combo lines")
        # check that the combo lines are correctly linked to each other
        parent_line_id = self.env['pos.order.line'].search([('product_id.name', '=', 'Office Combo'), ('order_id', '=', order.id)])
        combo_line_ids = self.env['pos.order.line'].search([('product_id.name', '!=', 'Office Combo'), ('order_id', '=', order.id)])
        self.assertEqual(parent_line_id.combo_line_ids, combo_line_ids, "The combo parent should have 3 combo lines")
        self.assertEqual(order.lines[1].price_unit, 13.66)
        self.assertAlmostEqual(order.lines[2].price_unit, 16.67)
        self.assertAlmostEqual(order.lines[3].price_unit, 18.67)
        # In the future we might want to test also if:
        #   - the combo lines are correctly stored in and restored from local storage
        #   - the combo lines are correctly shared between the pos configs ( in cross ordering )

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
        self.create_product('Product 1', 10, barcode='08431673020125')
        self.create_product('Product 2', 10, barcode='08431673020126')
        # 3760171283370 can be parsed with GS1 rules but it's not GS1
        self.create_product('Product 3', 10, barcode='3760171283370')
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('GS1BarcodeScanningTour')

    def test_gs1_barcode_scan_missing_product_variant(self):
        """
        Scanning a GS1 barcode for a product that is not loaded must add the specific
        matching variant, not the first variant of the template.
        """
        barcodes_gs1_nomenclature = self.env.ref("barcodes_gs1_nomenclature.default_gs1_nomenclature")
        default_nomenclature_id = self.env.ref("barcodes.default_barcode_nomenclature")
        self.main_pos_config.company_id.write({
            'nomenclature_id': barcodes_gs1_nomenclature.id,
        })
        self.main_pos_config.write({
            'fallback_nomenclature_id': default_nomenclature_id,
        })

        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'L', 'sequence': 1}),
                Command.create({'name': 'S', 'sequence': 2}),
            ],
        })
        product_tmpl = self.env['product.template'].create({
            'name': 'GS1 Missing Variant Product',
            'available_in_pos': False,
            'list_price': 10,
            'taxes_id': False,
            'attribute_line_ids': [Command.create({
                'attribute_id': size_attribute.id,
                'value_ids': [Command.set(size_attribute.value_ids.ids)],
            })],
        })

        variant_s = product_tmpl.product_variant_ids.filtered(
            lambda v: any(val.name == 'S' for val in v.product_template_attribute_value_ids.mapped('product_attribute_value_id'))
        )
        variant_s.write({'barcode': '5400000002649'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_gs1_barcode_scan_missing_product_variant', login="pos_user")

    def test_refund_order_with_fp_tax_included(self):
        # create a fiscal position
        self.fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'No Tax',
        })
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
            'fiscal_position_ids': self.fiscal_position,
            'original_tax_ids': self.tax1,
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
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'FiscalPositionNoTaxRefund', login="pos_user")
        order = self.env['pos.order'].search([])
        self.assertTrue(order[0].name == order[1].name + " REFUND")

    def test_limited_product_pricelist_loading(self):
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_product_count', 1)

        limited_category = self.env['pos.category'].create({'name': 'Limited Category'})

        product_1 = self.create_product('Test Product 1', 100, barcode='0100100', pos_categ_ids=[Command.set(limited_category.ids)])
        self.create_product('Test Product 3', 300, barcode='0100300', pos_categ_ids=[Command.set(limited_category.ids)])

        pricelist_item = self.env['product.pricelist.item'].create([{
            'applied_on': '3_global',
            'fixed_price': 50,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_1.id,
            'fixed_price': 80,
            'min_quantity': 1,
        }, {
            'applied_on': '0_product_variant',
            'product_id': product_1.id,
            'fixed_price': 70,
            'min_quantity': 2,
        }])
        self.main_pos_config.write({
            'iface_available_categ_ids': [],
            'limit_categories': True,
        })
        self.main_pos_config.pricelist_id.write({'item_ids': [(6, 0, pricelist_item.ids)]})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'limitedProductPricelistLoading', login="pos_user")

    def test_restricted_categories_combo_product(self):
        """
        Ensure combo choices product are always loaded if parent is in allowed categories, even when restricted categories are configured:
        - These combo choices should be visible when configuring the parent combo product but not be visible as product that we can directly sell inside POS
        - These combo choices should appear on the preparation ticket changes
        """
        pos_restricted_categ = self.env["pos.category"].create({
            "name": "Restricted product",
        })
        pos_other_categ = self.env["pos.category"].create({
            "name": "Other products",
        })
        self.env['pos.printer'].create({
            'name': 'Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '0.0.0.0',
            'use_type': 'preparation',
            'product_categories_ids': [Command.set(self.env['pos.category'].search([]).ids)],
        })

        self.main_pos_config.write({
            'use_order_printer': True,
            'preparation_printer_ids': [Command.set(self.env['pos.printer'].search([('use_type', '=', 'preparation')]).ids)],
            'limit_categories': True,
            'iface_available_categ_ids': [Command.set([pos_restricted_categ.id])],
        })
        self._setup_combo_product()
        self.office_combo.pos_categ_ids = [(6, 0, [pos_restricted_categ.id])]
        self.office_combo.combo_ids = [(6, 0, [self.desks_combo.id])]
        self.desks_combo.combo_item_ids[0].product_id.pos_categ_ids = [(6, 0, [pos_restricted_categ.id])]
        self.desks_combo.combo_item_ids[1].product_id.pos_categ_ids = [(6, 0, [pos_other_categ.id])]
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_restricted_categories_combo_product', login="pos_user")

    def test_translate_product_name(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.pos_user.write({'lang': 'fr_FR'})

        product = self.create_product('Test Product', 100)
        product.update_field_translations('name', {'fr_FR': 'Testez le produit'})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'TranslateProductNameTour', login="pos_user")

    def test_allow_order_modification_after_validation_error(self):
        """
        User error as a result of validation should block the order.
        Taking action by order modification should be allowed.
        """
        self.create_product('Test Product', 10)

        def sync_from_ui_patch(*_args, **_kwargs):
            raise UserError('Test Error')

        with patch.object(self.env.registry.models['pos.order'], "sync_from_ui", sync_from_ui_patch):
            # If there is problem in the tour, remove the log catcher to debug.
            with self.assertLogs(level="WARNING") as log_catcher:
                self.main_pos_config.with_user(self.pos_user).open_ui()
                self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'OrderModificationAfterValidationError', login="pos_user")

            warning_outputs = [o for o in log_catcher.output if 'WARNING' in o]
            self.assertEqual(len(warning_outputs), 1, "Exactly one warning should be logged")

    def test_order_refund_flow(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_order_refund_flow')
        self.assertEqual(self.env['mail.mail'].search_count([('email_to', '=', 'test@narendradamodardasmodi.com')]), 1)

    def test_refund_few_quantities(self):
        """ Test to check that refund works with quantities of less than 0.5 """
        self.create_product('Sugar', 3, uom_id=self.env.ref('uom.product_uom_kgm').id)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('RefundFewQuantities')

    def test_refund_multiple_products_amounts_compliance(self):
        test_product = self.create_product('Test Product', 10)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        current_session = self.main_pos_config.current_session_id

        self.start_pos_tour('refund_multiple_products_amounts_compliance')

        refund_order = current_session.order_ids.filtered(lambda order: order.is_refund)
        self.assertEqual(refund_order.lines[0].price_subtotal, 2 * test_product.list_price)
        self.close_pos_session()

        self.assertEqual(current_session.state, 'closed')
        report_refund_order, report_order = self.env['report.pos.order'].sudo().search([('order_id', 'in', current_session.order_ids.ids)])
        self.assertEqual(report_order.margin, 20.0)
        self.assertEqual(report_refund_order.margin, -20.0)
        self.assertEqual(report_order.price_total, 20.0)
        self.assertEqual(report_refund_order.price_total, -20.0)

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
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'ProductComboPriceCheckTour', login="pos_user")
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.type == 'combo').margin, 0)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.type == 'combo').margin_percent, 0)

    def test_customer_display_as_public(self):
        self.main_pos_config.customer_display_bg_img = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgYGAAAAAEAAH2FzhVAAAAAElFTkSuQmCC'
        response = self.url_open(f"/web/image/pos.config/{self.main_pos_config.id}/customer_display_bg_img")
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Shop.png' in response.headers['Content-Disposition'])

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
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'PosProductWithDynamicAttributes', login="pos_admin")

    def test_product_with_single_value_dynamic_attribute(self):
        """A dynamic attribute with a single value must not open the configurator but still
        creates the product variant on the server when added to the order."""
        dynamic_attribute = self.env['product.attribute'].create({
            'name': 'Single Dynamic Attribute',
            'create_variant': 'dynamic',
        })
        value = self.env['product.attribute.value'].create({
            'name': 'Only Value',
            'attribute_id': dynamic_attribute.id,
        })
        product_template = self.env['product.template'].create({
            'name': 'Single Dynamic Product',
            'list_price': 5.0,
            'taxes_id': False,
            'available_in_pos': True,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': dynamic_attribute.id,
            'value_ids': [Command.set([value.id])],
        })

        no_variant_attribute = self.env['product.attribute'].create({
            'name': 'No Variant Attribute',
            'create_variant': 'no_variant',
        })
        no_variant_value = self.env['product.attribute.value'].create({
            'name': 'No Variant Value',
            'attribute_id': no_variant_attribute.id,
        })
        mixed_template = self.env['product.template'].create({
            'name': 'Mixed Attribute Product',
            'list_price': 7.0,
            'taxes_id': False,
            'available_in_pos': True,
        })
        self.env['product.template.attribute.line'].create([
            {
                'product_tmpl_id': mixed_template.id,
                'attribute_id': dynamic_attribute.id,
                'value_ids': [Command.set([value.id])],
            },
            {
                'product_tmpl_id': mixed_template.id,
                'attribute_id': no_variant_attribute.id,
                'value_ids': [Command.set([no_variant_value.id])],
            },
        ])
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_product_with_single_value_dynamic_attribute', login="pos_user")

    def test_product_search(self):
        """Verify that the product search works correctly"""
        product_with_variant = self.create_product_template('Product with Variant', 10, barcode='1234567')

        color_attribute = self.env['product.attribute'].create({
            'name': 'Color always',
            'create_variant': 'always',
            'value_ids': [(0, 0, {
                'name': 'Red',
                'sequence': 1,
            }), (0, 0, {
                'name': 'Blue',
                'sequence': 2,
            })],
        })

        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_with_variant.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, color_attribute.value_ids.ids)]
        })
        product_with_variant.product_variant_ids[0].write({
            "barcode": "variant_barcode_1",
            "default_code": "VARIANT_1"
        })
        product_with_variant.product_variant_ids[1].write({
            "barcode": "variant_barcode_2",
            "default_code": "VARIANT_2"
        })

        self.create_product('Test Product 1', 100, barcode='1234567890123', default_code='TESTPROD1')
        self.create_product('Test Product 2', 100, barcode='1234567890124', default_code='TESTPROD2')
        self.create_product('Apple', 100)
        self.create_product('galaxy', 100)
        self.create_product('1234567890123', 100)

        att_color = self.env['product.attribute'].create({'name': 'Color', 'sequence': 1})

        att_color_values = self.env['product.attribute.value'].create([
            {'name': 'galaxy variant', 'attribute_id': att_color.id, 'sequence': 1},
            {'name': 'blue', 'attribute_id': att_color.id, 'sequence': 2},
        ])

        self.env['product.template'].create({
            'name': 'Test Product variant',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': att_color.id,
                    'value_ids': [Command.set(att_color_values.mapped('id'))],
                }),
            ],
            'available_in_pos': True,
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'ProductSearchTour', login="pos_user")

    def test_customer_popup(self):
        """Verify that the customer popup search & infinite scroll work properly"""
        # Preload enough partners to make the list scrollable without loading the new ones yet
        self.env['ir.config_parameter'].sudo().set_int('point_of_sale.limited_customer_count', 15)
        self.env["res.partner"].create([{"name": "Z partner to search"}, {"name": "Z partner to scroll"}])
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'CustomerPopupTour', login="pos_user")

    def test_tracking_number_closing_session(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_tracking_number_closing_session', login="accountman")

        # Change should be given in cash
        cash_payment_method = self.main_pos_config.payment_method_ids.filtered(lambda p: p.type == 'cash')
        last_order = self.main_pos_config.current_session_id.order_ids[-1]
        self.assertRecordValues(last_order.payment_ids.sorted(), [
            {'amount': -18.02, 'payment_method_id': cash_payment_method.id, 'is_change': True},
            {'amount': 20.0, 'payment_method_id': self.bank_payment_method.id, 'is_change': False},
        ])

        # References should not have gaps
        references = self.env['pos.order'].search([], order="pos_reference").mapped("pos_reference")
        for i in range(len(references) - 1):
            self.assertEqual(int(references[i + 1].split('-')[-1]), int(references[i].split('-')[-1]) + 1, "There is a gap in the pos references")

    def test_reload_page_before_payment_with_customer_account(self):
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'type': 'pay_later',
        })
        self.main_pos_config.write({'payment_method_ids': [(6, 0, self.customer_account_payment_method.ids)]})
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(
            f'/pos/ui/{self.main_pos_config.id}',
            'test_reload_page_before_payment_with_customer_account',
            login='pos_user',
        )

    @freeze_time("2025-06-15 11:09")
    def test_cash_in_out(self):
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_cash_in_out', login="pos_admin")

        self.assertEqual(len(self.main_pos_config.current_session_id.bank_statement_line_ids), 1, "There should be one cash in/out statement line")
        self.assertEqual(self.main_pos_config.current_session_id.bank_statement_line_ids[0].amount, -5, "The cash in/out amount should be -5")

    def test_edit_paid_order(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui/{self.main_pos_config.id}", 'test_edit_paid_order', login="pos_user")
        edited_orders = self.env['pos.order'].search([], limit=1)
        # check invoice created
        self.assertTrue(edited_orders[0].account_move)
        self.assertEqual(edited_orders[0].partner_id.name, 'Partner Test 1')

    def test_reuse_empty_floating_order(self):
        """ Verify that after a payment, POS should reuse an existing empty floating order if available, instead of always creating new ones """
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", 'test_reuse_empty_floating_order', login="pos_user")

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
        self.partner_test_1.property_payment_term_id = payment_term.id

        tax = self.env['account.tax'].create({
            'name': 'Tax 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        self.create_product('Product Test', 1000, [tax.id])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('PaymentScreenInvoiceOrder')

        order = self.env['pos.order'].search([('partner_id', '=', self.partner_test_1.id)], limit=1)
        self.assertTrue(order)

        self.assertEqual(order.partner_id, self.partner_test_1)

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
        self.start_tour('/pos/ui/%d' % self.main_pos_config.id, 'test_product_create_update_from_frontend', login='pos_admin')

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
        fiscal_position = self.env['account.fiscal.position'].create({
            'name': 'Fiscal Position Test',
        })
        tax_1 = self.env['account.tax'].create({
            'name': 'Tax 15%',
            'amount': 15,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_group_id': self.env['account.tax.group'].create({
                'name': 'Tax Group 15%',
                'company_id': self.env.company.id,
                'pos_receipt_label': 'Tax Group 1',
            }).id,
        })

        tax_2 = self.env['account.tax'].create({
            'name': 'Tax 5%',
            'amount': 5,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'tax_group_id': self.env['account.tax.group'].create({
                'name': 'Tax Group 5%',
                'company_id': self.env.company.id,
                'pos_receipt_label': 'Tax Group 2',
            }).id,
            'fiscal_position_ids': [Command.link(fiscal_position.id)],
            'original_tax_ids': [Command.link(tax_1.id)],
        })
        self.create_product('Test Product', 100, [tax_1.id])

        self.main_pos_config.write({
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [fiscal_position.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_fiscal_position_tax_group_labels')
        orders = self.main_pos_config.current_session_id.order_ids

        self.assertEqual(orders[0].fiscal_position_id.id, fiscal_position.id)
        self.assertEqual(orders[0].lines.tax_ids_after_fiscal_position.id, tax_2.id)
        self.assertEqual(orders[0].amount_total, 105)
        self.assertFalse(orders[1].fiscal_position_id)
        self.assertEqual(orders[1].lines.tax_ids_after_fiscal_position.id, tax_1.id)
        self.assertEqual(orders[1].amount_total, 115)

    def test_draft_orders_not_syncing(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_draft_orders_not_syncing', login="pos_user")
        n_draft_order = self.env['pos.order'].search_count([('state', '=', 'draft')], limit=1)
        self.assertEqual(n_draft_order, 0, 'There should be no draft orders created')

    def test_product_long_press(self):
        """ Test the long press on product to open the product info """
        self._archive_products()
        self.main_pos_config.company_id.country_id.vat_label = 'Should stay Tax even after editing vat_label'
        group_tax = self.env['account.tax'].create({
            'name': 'Parent Tax',
            'amount_type': 'group',
            'children_tax_ids': [(0, 0, {
                'name': 'Child Tax 1',
                'amount': 10,
            }), (0, 0, {
                'name': 'Child Tax 2',
                'amount': 5,
            })],
        })
        self.create_product('Test Product', 100, [group_tax.id])
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_product_long_press', login="pos_user")

    def test_zero_decimal_places_currency(self):
        zero_decimal_currency = self.env['res.currency'].create({
            'name': 'ZeroDecimalCurrency',
            'symbol': 'ZDC',
            'rounding': 1.0,
            'decimal_places': 0,
        })

        self.env.user.company_id.currency_id = zero_decimal_currency
        self.main_pos_config.available_pricelist_ids.write({'currency_id': zero_decimal_currency.id})
        self.create_product('Test Product', 100)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_zero_decimal_places_currency')
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(order.payment_ids[0].payment_method_id, self.main_pos_config.payment_method_ids[0])

    def test_barcode_search_attributes_preset(self):
        product = self.create_product_template('Product with Attributes', 10)
        # Product template to force UI reset (acts as a delay)
        self.create_product_template('Product without Attributes', 20, barcode='987654321')

        attribute_1, attribute_2, attribute_3, attribute_4 = self.env['product.attribute'].create([{
            'name': 'Attribute 1',
            'create_variant': 'always',
            'display_type': 'radio',
            'value_ids': [(0, 0, {
                'name': 'Value 1',
            }), (0, 0, {
                'name': 'Value 2',
            })],
        }, {
            'name': 'Attribute 2',
            'create_variant': 'always',
            'display_type': 'pills',
            'value_ids': [(0, 0, {
                'name': 'Value 3',
            }), (0, 0, {
                'name': 'Value 4',
            })],
        }, {
            'name': 'Attribute 3',
            'create_variant': 'always',
            'display_type': 'select',
            'value_ids': [(0, 0, {
                'name': 'Value 5',
            }), (0, 0, {
                'name': 'Value 6',
            })],
        }, {
            'name': 'Attribute 4',
            'create_variant': 'always',
            'display_type': 'color',
            'value_ids': [(0, 0, {
                'name': 'Value 7',
            }), (0, 0, {
                'name': 'Value 8',
            })],
        }])

        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product.id,
            'attribute_id': attribute_1.id,
            'value_ids': [(6, 0, attribute_1.value_ids.ids)],
            'sequence': 1,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_2.id,
            'value_ids': [(6, 0, attribute_2.value_ids.ids)],
            'sequence': 2,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_3.id,
            'value_ids': [(6, 0, attribute_3.value_ids.ids)],
            'sequence': 3,
        }, {
            'product_tmpl_id': product.id,
            'attribute_id': attribute_4.id,
            'value_ids': [(6, 0, attribute_4.value_ids.ids)],
            'sequence': 4,
        }])

        for p in product.product_variant_ids:
            p.write({
                'barcode': f'1234{"".join(p.product_template_attribute_value_ids.mapped(lambda ptav: ptav.name[-1]))}',
            })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_barcode_search_attributes_preset', login="pos_user")

    def test_auto_validate_force_done(self):
        self.main_pos_config.write({
            'auto_validate_electronic_payment': True
        })
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_auto_validate_force_done', login="pos_user")

    def test_pos_ui_round_globally(self):
        self.main_pos_config.company_id.tax_calculation_rounding_method = 'round_globally'
        tax_16 = self.env['account.tax'].create({
            'name': 'Tax 16%',
            'amount': 16,
        })
        self.create_product('Test Product 1', 7051.73, [tax_16.id])
        self.create_product('Test Product 2', 352.59, [tax_16.id])
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_pos_ui_round_globally')

        pos_session = self.main_pos_config.current_session_id
        self.assertEqual(pos_session.order_ids[0].payment_ids[0].amount, 7771.0)

        # Close the session and check the session journal entry.
        pos_session.close_session_from_ui()

        lines = pos_session.move_ids.line_ids.sorted('balance')

        self.assertEqual(len(lines), 3, "There should be 3 lines in the session journal entry")
        self.assertAlmostEqual(lines[0].balance, -6699.14)  # Negative line and positive are aggregated
        self.assertAlmostEqual(lines[1].balance, -1071.86)  # Negative line and positive are aggregated
        self.assertAlmostEqual(lines[2].balance, 7771.0)

    def test_preset_timing_retail(self):
        """
        Test to set order preset hour inside a tour
        """
        self.preset_dine_in = self.env['pos.preset'].create({
            'name': 'Dine in',
        })
        self.preset_delivery = self.env['pos.preset'].create({
            'name': 'Delivery',
            'identification': 'address',
        })
        self.main_pos_config.write({
            'use_presets': True,
            'default_preset_id': self.preset_dine_in.id,
            'available_preset_ids': [(6, 0, [self.preset_delivery.id])],
        })
        self.pos_user.street = 'Rue de Ramillies'
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Takeaway',
            'attendance_ids': [(0, 0, {
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
            }) for day in range(7)],
        })
        self.preset_delivery.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar
        })
        self.start_pos_tour('test_preset_timing_retail')

    def test_pricelists_in_pos(self):
        pos_limited_category = self.env['pos.category'].create({'name': 'Limited Category'})
        pos_category = self.env['pos.category'].create({'name': 'test_pricelists_in_pos'})
        product_category = self.env['product.category'].create({'name': 'test_pricelists_in_pos'})
        orange_category = self.env['product.category'].create({'name': 'Orange Category'})

        def generate_pricelist_items(pricelist, fixed_price, product=None, product_tmpl=None, product_category=None):
            applied_on = '0_product_variant' if product else '1_product' if product_tmpl else '2_product_category' if product_category else '3_global'
            return self.env['product.pricelist.item'].create({
                'pricelist_id': pricelist.id,
                'product_id': product.id if product else False,
                'product_tmpl_id': product_tmpl.id if product_tmpl else False,
                'categ_id': product_category.id if product_category else False,
                'compute_price': 'fixed',
                'applied_on': applied_on,
                'fixed_price': fixed_price,
            })

        def generate_product_template_with_attributes(name, price, pos_category=None, product_category=None):
            size_attribute = self.env['product.attribute'].create({
                'name': 'Size',
                'sequence': 4,
                'value_ids': [(0, 0, {
                    'name': 'BIG',
                    'sequence': 1,
                }), (0, 0, {
                    'name': 'MEDIUM',
                    'sequence': 2,
                }), (0, 0, {
                    'name': 'SMALL',
                    'sequence': 3,
                })],
            })

            product_tmpl = self.env['product.template'].create({
                'name': name.capitalize(),
                'available_in_pos': True,
                'categ_id': product_category.id if product_category else False,
                'pos_categ_ids': [(4, pos_category.id)] if pos_category else False,
                'list_price': price,
                'taxes_id': False,
                'attribute_line_ids': [(0, 0, {
                    'attribute_id': size_attribute.id,
                    'value_ids': [(6, 0, size_attribute.value_ids.ids)]
                })],
            })

            for index, variant in enumerate(product_tmpl.product_variant_ids):
                variant.write({'barcode': f'{name}_{index}'})

            return product_tmpl

        banana = generate_product_template_with_attributes('banana', 10.00, pos_category)
        apple = generate_product_template_with_attributes('apple', 5.00, False, product_category)
        pear = generate_product_template_with_attributes('pear', 2.00)
        lime = generate_product_template_with_attributes('lime', 1.00)
        orange = generate_product_template_with_attributes('orange', 3.00, False, orange_category)
        kiwi = generate_product_template_with_attributes('kiwi', 4.00)

        test_pricelist = self.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })

        percentage_pricelist = self.env['product.pricelist'].create({
            'name': 'Percentage Pricelist',
        })

        generate_pricelist_items(test_pricelist, 20, False, banana)
        generate_pricelist_items(test_pricelist, 100, banana.product_variant_ids[0])
        generate_pricelist_items(test_pricelist, 150, banana.product_variant_ids[1])
        generate_pricelist_items(test_pricelist, 500, False, False, product_category)
        generate_pricelist_items(test_pricelist, 1000, False, False, orange_category)
        generate_pricelist_items(test_pricelist, 100, apple.product_variant_ids[0])
        generate_pricelist_items(test_pricelist, 20, pear.product_variant_ids[0])
        generate_pricelist_items(test_pricelist, 40, pear.product_variant_ids[1])
        generate_pricelist_items(test_pricelist, 60, pear.product_variant_ids[2])
        generate_pricelist_items(test_pricelist, 100, False, lime)
        generate_pricelist_items(test_pricelist, 200, lime.product_variant_ids[1])
        generate_pricelist_items(test_pricelist, 400, lime.product_variant_ids[2])
        generate_pricelist_items(test_pricelist, 600, orange.product_variant_ids[1])
        generate_pricelist_items(test_pricelist, 500, orange.product_variant_ids[2])
        generate_pricelist_items(test_pricelist, 10)
        generate_pricelist_items(test_pricelist, 20, kiwi.product_variant_ids[0])

        self.env['product.pricelist.item'].create({
            'pricelist_id': percentage_pricelist.id,
            'base': 'pricelist',
            'base_pricelist_id': test_pricelist.id,
            'compute_price': 'discount',
            'price_discount': 50,
            'applied_on': '3_global',
        })

        self.main_pos_config.write({
            "limit_categories": True,
            "iface_available_categ_ids": [(6, 0, [pos_limited_category.id])],
            'available_pricelist_ids': [(6, 0, [test_pricelist.id, percentage_pricelist.id])],
            'pricelist_id': test_pricelist.id,
        })

        load_data_from_pos_stats = {'count': 0, 'items': {}}

        # Test product exclusion
        cherry = generate_product_template_with_attributes('cherry', 2.00)
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 5,
            'value_ids': [(0, 0, {
                'name': 'RED',
                'sequence': 1,
            }), (0, 0, {
                'name': 'GREEN',
                'sequence': 2,
            }), (0, 0, {
                'name': 'BLUE',
                'sequence': 3,
            })],
        })
        cherry.attribute_line_ids = [(0, 0, {
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, color_attribute.value_ids.ids)]
        })]
        color_attribute = cherry.attribute_line_ids.filtered(lambda l: l.attribute_id.name == 'Color')
        first_color_value = color_attribute.product_template_value_ids.filtered(lambda v: v.attribute_id.name == 'Color' and v.name == 'RED')
        first_size_value = cherry.product_variant_ids.product_template_attribute_value_ids.filtered(lambda v: v.attribute_id.name == 'Size' and v.name == 'BIG')
        first_color_value.excluded_value_ids = [Command.link(value) for value in first_size_value.ids]
        for index, variant in enumerate(cherry.product_variant_ids):
            variant.write({'barcode': f'cherry_{index}'})

        def load_data_patch(self, local_data={}):
            if 'product.template' in local_data.get('models', []) and len(local_data.get('search_params', {})) > 0:
                load_data_from_pos_stats['count'] += 1
            result = super(self.env.registry.models['pos.session'], self).load_data(local_data)
            if 'product.template' in local_data.get('models', []) and len(local_data.get('search_params', {})) > 0:
                lowered_name = result['product.template'][0]['display_name'].lower()
                load_data_from_pos_stats['items'][lowered_name] = len(result['product.pricelist.item'])
            return result
        with patch.object(self.env.registry.models['pos.session'], "load_data", load_data_patch):
            self.start_pos_tour('test_pricelists_in_pos')

        # Should load 7 different products, since 7 products were created
        # The stack count is 14 since load_data is called by the frontend (loadNewProducts)
        # and by the backend (notify_synchronisation) after the frontend dispatch its new data
        self.assertEqual(load_data_from_pos_stats['count'], 14)

        # Length of loaded pricelist items should correspond to the number of items linked
        # to the product template or product variant
        # Global rules are loaded at starting of the PoS
        self.assertEqual(load_data_from_pos_stats['items']['banana'], 3, "Banana should have 3 pricelist items")
        self.assertEqual(load_data_from_pos_stats['items']['apple'], 1, "Apple should have 1 pricelist item")
        self.assertEqual(load_data_from_pos_stats['items']['pear'], 3, "Pear should have 3 pricelist items")
        self.assertEqual(load_data_from_pos_stats['items']['lime'], 3, "Lime should have 3 pricelist items")
        self.assertEqual(load_data_from_pos_stats['items']['orange'], 2, "Orange should have 2 pricelist items")
        self.assertEqual(load_data_from_pos_stats['items']['kiwi'], 1, "Kiwi should have 1 pricelist item")

    def test_fast_payment_validation_from_product_screen_without_automatic_receipt_printing(self):
        self.preset_delivery = self.env['pos.preset'].create({
            'name': 'Delivery',
            'identification': 'address',
        })
        self.main_pos_config.write({
            'use_fast_payment': True,
            'use_presets': True,
            'fast_payment_method_ids': [(6, 0, self.bank_payment_method.ids)],
            'default_preset_id': self.preset_delivery.id,
            'available_preset_ids': [(6, 0, [self.preset_delivery.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_fast_payment_validation_from_product_screen_without_automatic_receipt_printing')
        order1 = self.main_pos_config.current_session_id.order_ids[0]
        order2 = self.main_pos_config.current_session_id.order_ids[1]
        self.assertEqual(order1.state, 'paid', "The order should be paid after the fast payment validation")
        self.assertEqual(len(order1.payment_ids), 1, "There should be one payment line used for the fast payment")
        self.assertEqual(order1.payment_ids.payment_method_id, self.bank_payment_method, "The payment method used should be the bank payment method")
        self.assertEqual(order2.state, 'paid', "The order should be paid")
        self.assertEqual(len(order2.payment_ids), 1, "There should be one payment line")
        self.assertEqual(order2.payment_ids.payment_method_id, self.bank_payment_method, "The payment method used should be the bank payment method")

    def test_fast_payment_validation_from_product_screen_with_automatic_receipt_printing(self):
        pos_printer = self.env['pos.printer'].create({
            'name': 'Printer',
            'printer_type': 'epson_epos',
            'printer_ip': '1.0.1.0',
            'use_type': 'receipt',
        })
        # Ensure duplicating a printer preserves its configured IP address,
        copied_printer_data = pos_printer.copy_data()
        self.assertEqual(
            copied_printer_data[0]['printer_ip'],
            '1.0.1.0',
            "The copied printer should preserve the original printer IP address.",
        )
        self.main_pos_config.write({
            'use_fast_payment': True,
            'fast_payment_method_ids': [(6, 0, self.bank_payment_method.ids)],
            'iface_print_auto': True,
            'other_devices': True,
            'receipt_printer_ids': [Command.set(pos_printer.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_fast_payment_validation_from_product_screen_with_automatic_receipt_printing')
        order1 = self.main_pos_config.current_session_id.order_ids[0]
        order2 = self.main_pos_config.current_session_id.order_ids[1]
        self.assertEqual(order1.state, 'paid', "The order should be paid after the fast payment validation")
        self.assertEqual(len(order1.payment_ids), 1, "There should be one payment line used for the fast payment")
        self.assertEqual(order1.payment_ids.payment_method_id, self.bank_payment_method, "The payment method used should be the bank payment method")
        self.assertEqual(order2.state, 'paid', "The order should be paid")
        self.assertEqual(len(order2.payment_ids), 1, "There should be one payment line")
        self.assertEqual(order2.payment_ids.payment_method_id, self.bank_payment_method, "The payment method used should be the bank payment method")

    def test_consistent_refund_process_between_frontend_and_backend(self):
        """
        Ensure that the partial refund process is consistent between the frontend and backend.
        This includes validating the refund order creation, amount, state, and payment processing.
        """
        # Open POS UI with the POS user
        pricelists = self.env['product.pricelist'].create([
            {'name': 'Test Pricelist'},
            {'name': 'Percentage Pricelist'},
        ])
        self.main_pos_config.write({
            'available_pricelist_ids': [Command.set(pricelists.ids)],
            'pricelist_id': pricelists[0].id,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()

        # Run the POS tour simulating a partial refund
        self.start_pos_tour('test_consistent_refund_process_between_frontend_and_backend')

        # Fetch orders created in the current POS session
        orders = self.env['pos.order'].search([
            ('session_id', '=', self.main_pos_config.current_session_id.id),
        ])
        self.assertEqual(len(orders), 2, "Expected two orders: original and refund.")
        refunded = orders.filtered(lambda o: o.is_refund)
        order = orders - refunded
        self.assertEqual(
            refunded.pricelist_id.id,
            order.pricelist_id.id,
            "Refund order pricelist should be the original order's pricelist.",
        )

        # Perform refund on order and retrieve the resulting draft refund order
        refund_action = order.refund()
        backend_refund_order = self.env['pos.order'].browse(refund_action['res_id'])

        # Validate the refund order is in draft and has correct negative total
        self.assertEqual(backend_refund_order.state, 'draft', "Refund order should be in draft state.")

        # Create a payment for the refund using the configured bank method
        payment_context = {
            "active_id": backend_refund_order.id,
        }
        refund_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': backend_refund_order.amount_total,
            'payment_method_id': self.bank_payment_method.id,
        })

        # Validate and finalize the refund payment
        refund_payment.with_context(**payment_context).check()
        self.assertEqual(backend_refund_order.state, 'paid', "Refund order should be marked as paid.")

        # Lines are always positive even in refunds
        self.assertTrue(backend_refund_order.lines.price_subtotal > 0)
        self.assertTrue(refunded.lines.price_subtotal > 0)
        self.assertTrue(backend_refund_order.lines.price_subtotal_incl > 0)
        self.assertTrue(refunded.lines.price_subtotal_incl > 0)

        # Refund order total should be negative (qty = -1)
        self.assertTrue(backend_refund_order.amount_total < 0)
        self.assertTrue(refunded.amount_total < 0)

    def test_paid_order_with_archived_product_loads(self):
        """ Test that a paid order with archived products can be loaded in the POS. """
        archived_product = self.create_product('Archived Product', 10, active=False)

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.create_pos_order([[archived_product, 1, 0, {'price_unit': 10}]], pos_reference='1000-004-00002')
        self.start_pos_tour('test_paid_order_with_archived_product_loads')

    def test_search_more_skips_archived_variant(self):
        """ Search more must not load an archived variant matched by its internal reference. """
        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': 'S', 'sequence': 1}),
                Command.create({'name': 'XL', 'sequence': 2}),
            ],
        })
        product_tmpl = self.env['product.template'].create({
            'name': 'Archived Variant Shirt',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'attribute_line_ids': [Command.create({
                'attribute_id': size_attribute.id,
                'value_ids': [Command.set(size_attribute.value_ids.ids)],
            })],
        })
        variant_xl = product_tmpl.product_variant_ids.filtered(
            lambda v: v.product_template_attribute_value_ids.name == 'XL'
        )
        variant_xl.write({'default_code': 'SHIRT-XL-ARCHIVED', 'active': False})

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_search_more_skips_archived_variant')

    def test_order_invoice_search(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.pos_user.group_ids = [Command.link(self.env.ref('account.group_account_invoice').id)]
        self.start_tour("/pos/ui/%d" % self.main_pos_config.id, 'test_order_invoice_search', login="pos_user")

    def test_load_pos_demo_data(self):
        """ Test that the demo data can be loaded by admin but not by user. """

        if loaded_demo_data(self.env):
            self.skipTest('Cannot test with demo data.')

        # archive existing product records
        self._archive_products()

        # cannot load by pos user
        self.start_pos_tour('test_load_pos_demo_data_by_pos_user', login='pos_user')
        products = self.env['product.template'].search_count([('available_in_pos', '=', True)])
        self.assertFalse(products, 'Demo data should not be loaded by user.')

        # Member role with POS Administrator access
        self.pos_user.write({'group_ids': [
            Command.set(
                [
                    self.env.ref('base.group_user').id,
                    self.env.ref('point_of_sale.group_pos_manager').id,
                    self.env.ref('account.group_account_manager').id,
                ]
            )
        ]})
        self.start_pos_tour('test_load_pos_demo_data_with_member_role', login='pos_user')
        products = self.env['product.template'].search_count([('available_in_pos', '=', True)])
        self.assertFalse(products, 'Demo data should not be loaded by user with member role.')

    def test_cross_exclusion_attribute_values(self):
        """ If you create a product with two attributes and 2 values for each attribute, and you exclude one value of the first attribute with one value of the second attribute
        and vice versa, you should still be able to select the other values of the attributes. """
        self.attribute_1 = self.env['product.attribute'].create({
            'name': 'attribute_1',
            'create_variant': 'no_variant',
        })

        self.attribute_2 = self.env['product.attribute'].create({
            'name': 'attribute_2',
            'create_variant': 'no_variant',
        })

        self.attribute_1_value_1 = self.env['product.attribute.value'].create({
            'name': 'attribute_1_value_1',
            'attribute_id': self.attribute_1.id,
        })
        self.attribute_1_value_2 = self.env['product.attribute.value'].create({
            'name': 'attribute_1_value_2',
            'attribute_id': self.attribute_1.id,
        })
        self.attribute_2_value_1 = self.env['product.attribute.value'].create({
            'name': 'attribute_2_value_1',
            'attribute_id': self.attribute_2.id,
        })
        self.attribute_2_value_2 = self.env['product.attribute.value'].create({
            'name': 'attribute_2_value_2',
            'attribute_id': self.attribute_2.id,
        })

        self.test_product_1 = self.env['product.template'].create({
            'name': 'Test Product 1',
            'available_in_pos': True,
            'list_price': 10.0,
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': self.attribute_1.id,
                    'value_ids': [(6, 0, [self.attribute_1_value_1.id, self.attribute_1_value_2.id])],
                }),
                (0, 0, {
                    'attribute_id': self.attribute_2.id,
                    'value_ids': [(6, 0, [self.attribute_2_value_1.id, self.attribute_2_value_2.id])],
                }),
            ],
        })

        # Test the exclusion of attribute values
        ptav_1_1 = self.test_product_1.attribute_line_ids.filtered(lambda l: l.attribute_id.id == self.attribute_1.id).product_template_value_ids.filtered(lambda v: v.product_attribute_value_id.id == self.attribute_1_value_1.id)
        ptav_1_2 = self.test_product_1.attribute_line_ids.filtered(lambda l: l.attribute_id.id == self.attribute_1.id).product_template_value_ids.filtered(lambda v: v.product_attribute_value_id.id == self.attribute_1_value_2.id)
        ptav_2_2 = self.test_product_1.attribute_line_ids.filtered(lambda l: l.attribute_id.id == self.attribute_2.id).product_template_value_ids.filtered(lambda v: v.product_attribute_value_id.id == self.attribute_2_value_2.id)
        ptav_2_1 = self.test_product_1.attribute_line_ids.filtered(lambda l: l.attribute_id.id == self.attribute_2.id).product_template_value_ids.filtered(lambda v: v.product_attribute_value_id.id == self.attribute_2_value_1.id)

        ptav_1_1.excluded_value_ids = [Command.link(ptav_2_1.id)]
        ptav_1_2.excluded_value_ids = [Command.link(ptav_2_2.id)]

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_cross_exclusion_attribute_values')

    def test_weight_product(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_weight_product')
        order = self.env['pos.order'].search([], limit=1)
        self.assertEqual(len(order.lines), 2, "There should be two order lines")
        self.assertEqual(order.lines[0].price_subtotal_incl, 40, "The price unit should be 40")
        self.assertEqual(order.lines[0].qty, 4, "The quantity should be 4")
        self.assertEqual(order.lines[1].price_subtotal_incl, 40, "The price unit should be 40")
        self.assertEqual(order.lines[1].qty, 1, "The quantity should be 1")

    def test_sync_from_ui_one_by_one(self):
        """
        Sync from UI is now syncing orders one by one.
        sync_from_ui should be called 6 times in this tour (6 orders created).
        """

        pos_order = self.env.registry.models['pos.order']
        sync_counter = {'count': 0}

        @api.model
        def sync_from_ui_patch(self, orders):
            sync_counter['count'] += 1
            return super(pos_order, self).sync_from_ui(orders)

        with patch.object(pos_order, "sync_from_ui", sync_from_ui_patch):
            self.start_pos_tour("test_sync_from_ui_one_by_one", login="pos_user")
            self.assertEqual(sync_counter['count'], 6)

    def test_set_opening_note_without_cash_method(self):
        cash_method = self.main_pos_config.payment_method_ids.filtered(lambda pm: pm.type == 'cash')
        self.main_pos_config.payment_method_ids -= cash_method
        self.main_pos_config.with_user(self.pos_user).open_ui()
        current_session = self.main_pos_config.current_session_id
        self.start_pos_tour('test_set_opening_note_without_cash_method')
        self.assertEqual(current_session.opening_notes, 'Opening Notes')

    def test_product_configurator_price(self):
        """ Test that the product configurator displays the correct price when selecting attributes that impact the price. """
        self.env['product.template'].search([('available_in_pos', '=', True)]).active = False
        fiscal_position = self.env['account.fiscal.position'].create({'name': 'Include to Exclude'})
        self.taxes['tax10_incl'].write({
            'fiscal_position_ids': fiscal_position,
            'original_tax_ids': self.taxes['tax10'],
        })
        product = self.create_product_template('Configurable Product', 10, tax_ids=[self.taxes['tax10'].id])
        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
        })
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'no_variant',
        })
        small_size_value, large_size_value = self.env['product.attribute.value'].create([{
            'name': 'Small',
            'attribute_id': size_attribute.id,
        }, {
            'name': 'Large',
            'attribute_id': size_attribute.id,
        }])
        red_color_value, blue_color_value = self.env['product.attribute.value'].create([{
            'name': 'Red',
            'attribute_id': color_attribute.id,
        }, {
            'name': 'Blue',
            'attribute_id': color_attribute.id,
        }])
        size_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product.id,
            'attribute_id': size_attribute.id,
            'value_ids': [(6, 0, [small_size_value.id, large_size_value.id])],
        })
        size_line.product_template_value_ids[1].price_extra = 1
        color_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product.id,
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, [red_color_value.id, blue_color_value.id])],
        })
        color_line.product_template_value_ids[0].price_extra = 2
        color_line.product_template_value_ids[1].price_extra = 3

        pricelist_1, pricelist_2 = self.env['product.pricelist'].create([{
            'name': 'Pricelist 1',
        }, {
            'name': 'Pricelist 2',
            'item_ids': [(0, 0, {
                'applied_on': '1_product',
                'product_tmpl_id': product.id,
                'fixed_price': 20.0,
            })],
        }])
        self.main_pos_config.write({
            'available_pricelist_ids': [(6, 0, [pricelist_1.id, pricelist_2.id])],
            'pricelist_id': pricelist_1.id,
            'tax_regime_selection': True,
            'fiscal_position_ids': [(6, 0, [fiscal_position.id])],
        })
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_product_configurator_price', login="pos_user")

    def test_not_available_pricelist_not_set_on_order(self):
        """ Test that when the pricelist is not available, it is not set on the order """
        not_available_pricelist, available_pricelist = self.env['product.pricelist'].create([{
            'name': 'Not Available Pricelist',
        }, {
            'name': 'Available Pricelist',
        }])

        self.main_pos_config.write({
            'available_pricelist_ids': [(4, available_pricelist.id)],
            'pricelist_id': available_pricelist.id,
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()

        partner = self.env['res.partner'].create({
            'name': 'AA Customer',
            'property_product_pricelist': not_available_pricelist.id,
        })
        self.create_pos_order(
            [[self.wall_shelf.product_variant_ids[0], 1, 0, {'price_unit': 10.0}]],
            pos_reference='Test/0001',
        )

        self.start_pos_tour('test_not_available_pricelist_not_set_on_order')

        created_order = self.env['pos.order'].search([('partner_id', '=', partner.id)], limit=1)
        self.assertNotEqual(created_order.pricelist_id, not_available_pricelist)

    def test_pos_open_ui_button(self):
        """ Test the Open Register button click behavior in the dashboard. """
        self.env['pos.session'].create({'name': 'Test Session', 'config_id': self.main_pos_config.id, 'user_id': self.pos_user.id})  # Skip the tax inclusion selection if not the first session opening
        self.start_tour("/odoo/point-of-sale", 'test_pos_open_ui_button', login="pos_user")

    def test_customer_search_prefilled_on_create(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_customer_search_prefilled_on_create')

    def test_dynamic_barcode_extra(self):
        """
        Tests that a dynamic product with extra price has the right price when
        added to the order via its barcode
        """
        dynamic_attribute = self.env['product.attribute'].create({
            'name': 'Dynamic Attribute',
            'create_variant': 'dynamic',
        })
        value_1, value_2 = self.env['product.attribute.value'].create([
            {
                'name': 'M',
                'attribute_id': dynamic_attribute.id,
            },
            {
                'name': 'L',
                'default_extra_price': 10,
                'attribute_id': dynamic_attribute.id,
            }
        ])
        product_template = self.env['product.template'].create({
            'name': 'Dynamic Product',
            'is_storable': True,
            'list_price': 30.0,
            'available_in_pos': True,
            'taxes_id': [],
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': dynamic_attribute.id,
                    'value_ids': [Command.set([value_1.id, value_2.id])],
                }),
            ],
        })
        ptav_value_2 = product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda v: v.product_attribute_value_id == value_2
        )
        self.env['product.product'].create({
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [Command.set(ptav_value_2.ids)],
            'barcode': '1234567890',
        })

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour('test_dynamic_barcode_extra', login="pos_admin")

    def test_saver_screen_close_overlays(self):
        """Test that active overlays (e.g., dropdown menus) are closed when the SaverScreen is triggered."""
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('SaverScreenCloseOverlaysTour')

    def test_default_fiscal_position_allowed(self):
        """
        Tests that when a fiscal position is used through the detect automatically
        setting, it will not be chosen if it's not allowed in the PoS settings.
        """
        _, fp_allowed = self.env['account.fiscal.position'].create([
            {
                'name': 'Not Good',
                'auto_apply': True,
                'sequence': 1,
                'country_id': self.env.ref('base.us').id,
            },
            {
                'name': 'Allowed',
                'auto_apply': False,
                'sequence': 2,
            }
        ])
        self.partner_test_1.country_id = self.env.ref('base.us').id
        self.main_pos_config.write({
            'tax_regime_selection': True,
            'default_fiscal_position_id': fp_allowed.id,
            'fiscal_position_ids': [Command.set(fp_allowed.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_pos_tour('test_default_fiscal_position_allowed', login="pos_user")

    def test_barcode_scan_preselect_always_variant(self):
        """
        When scanning a barcode that matches a specific variant, the product configurator
        should open with the 'always' variant attribute (Color) preselected and only the
        'no_variant' attribute (Size) requiring user input.
        """
        color_attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'always',
            'display_type': 'radio',
            'value_ids': [(0, 0, {'name': 'Red', 'sequence': 1}), (0, 0, {'name': 'Blue', 'sequence': 2})],
        })
        size_attribute = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'no_variant',
            'display_type': 'radio',
            'value_ids': [(0, 0, {'name': 'Small', 'sequence': 1}), (0, 0, {'name': 'Large', 'sequence': 2})],
        })
        product = self.env['product.template'].create({
            'name': 'Variant Barcode Product',
            'available_in_pos': True,
            'list_price': 10,
            'taxes_id': False,
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': color_attribute.id,
                    'value_ids': [(6, 0, color_attribute.value_ids.ids)],
                }),
                (0, 0, {
                    'attribute_id': size_attribute.id,
                    'value_ids': [(6, 0, size_attribute.value_ids.ids)],
                }),
            ],
        })
        red_variant, blue_variant = product.product_variant_ids
        red_variant.barcode = 'VAR_RED_001'
        blue_variant.barcode = 'VAR_BLUE_001'

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_barcode_scan_preselect_always_variant', login="pos_user")

    def test_price_extra_pricelist_based_pricelist(self):
        """
        Tests that extra price is carried over when changing to a pricelist based pricelist
        """
        extra_attribute = self.env['product.attribute'].create({
            'name': 'Extra attribute',
            'create_variant': 'no_variant',
        })
        extra_value = self.env['product.attribute.value'].create({
            'name': 'Extra value',
            'attribute_id': extra_attribute.id,
        })
        attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.whiteboard_pen.id,
            'attribute_id': extra_attribute.id,
            'value_ids': [Command.set(extra_value.ids)]
        })
        attribute_line.product_template_value_ids[0].price_extra = 100

        pricelist_1 = self.env['product.pricelist'].create({'name': 'Pricelist 1'})
        pricelist_2 = self.env['product.pricelist'].create({
            'name': 'Pricelist 2',
            'item_ids': [Command.create({
                'compute_price': 'discount',
                'base': 'pricelist',
                'base_pricelist_id': pricelist_1.id,
                'price_discount': 50,
                'applied_on': '3_global',
            })],
        })

        self.main_pos_config.write({
            'pricelist_id': pricelist_1.id,
            'available_pricelist_ids': [Command.set([pricelist_1.id, pricelist_2.id])],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_price_extra_pricelist_based_pricelist', login="pos_user")

    def test_baseline_between_frontend_and_backend(self):
        company = self.main_pos_config.company_id
        company.tax_calculation_rounding_method = 'round_globally'

        only_categ = self.env['pos.category'].create({'name': 'Only Category'})
        self.main_pos_config.write({
            'limit_categories': True,
            'iface_available_categ_ids': [(6, 0, [only_categ.id])],
        })
        tax_16 = self.env['account.tax'].create({
            'name': 'Tax 16%',
            'amount': 16,
        })
        self.create_product('Test Product 1', 7051.73, [tax_16.id], pos_categ_ids=[only_categ.id])
        self.create_product('Test Product 2', 352.59, [tax_16.id], pos_categ_ids=[only_categ.id])

        def get_frontend_data(self, frontend_data):
            frontend_data = json.loads(frontend_data)
            base_lines = self.lines._prepare_base_lines_for_taxes_computation()
            zipped = zip(frontend_data['baseLines'], base_lines)
            for frontend_line, backend_line in zipped:
                if frontend_line.get('is_refund', False) != backend_line['is_refund']:
                    error = "Refund status mismatch between frontend and backend"
                    raise ValueError(error)

                if frontend_line.get('quantity', 0) != backend_line['quantity']:
                    error = "Quantity mismatch between frontend and backend"
                    raise ValueError(error)

                if frontend_line.get('sign') != backend_line['sign']:
                    error = "Sign mismatch between frontend and backend"
                    raise ValueError(error)

        order_model = self.env.registry.models['pos.order']
        with patch.object(order_model, 'get_frontend_data', get_frontend_data, create=True):
            self.start_pos_tour('test_baseline_between_frontend_and_backend')
        self.close_pos_session()


# This class just runs the same tests as above but with mobile emulation
class MobileTestUi(TestUi):
    _test_user_groups = None  # FIXME list needed groups

    browser_size = '375x667'
    touch_enabled = True
    allow_inherited_tests_method = True
