# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestPoSProductVariants(ProductVariantsCommon, TestPointOfSaleHttpCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_integration_dynamic_variant_price(self):
        """Tests the price of products with dynamic variant when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 10,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dynamic product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        })

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids.id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, [ptav_dyn2.id])],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_variant_price', login="pos_user")

    def test_integration_always_variant_price(self):
        """Tests the price of products with always variant when added to cart"""
        self.size_attribute_m.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A always product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_always_variant_price', login="pos_user")

    def test_integration_never_variant_price(self):
        """Tests the price of products with no variant(never) variant when added to cart"""
        self.no_variant_attribute_second.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A never product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_never_variant_price', login="pos_user")

    def test_integration_dynamic_always_variant_price(self):
        """Tests the price of products with dynamic and always variants when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 20,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/alw product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_always1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.size_attribute_s.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_always1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_always_variant_price', login="pos_user")

    def test_integration_dynamic_never_variant_price(self):
        """Tests the price of products with dynamic and never variants when added to cart"""
        self.env['product.attribute.value'].create({
            'name': 'dyn3',
            'attribute_id': self.dynamic_attribute.id,
            'default_extra_price': 20,
        })
        (dyn1, dyn2, dyn3) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.no_variant_attribute_second.default_extra_price = 5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/nev product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id, dyn3.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_never1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.no_variant_attribute_extra.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_never1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_never_variant_price', login="pos_user")

    def test_integration_always_never_variant_price(self):
        """Tests the price of products with always and never variants when added to cart"""
        self.no_variant_attribute_second.default_extra_price = 5
        self.size_attribute_m.default_extra_price = 10

        product_template = self.env['product.template'].create({
            'name': 'A alw/nev product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_always_never_variant_price', login="pos_user")

    def test_integration_dynamic_always_never_variant_price(self):
        """Tests the price of products with all types of variants when added to cart"""
        (dyn1, dyn2) = self.dynamic_attribute.value_ids
        dyn2.default_extra_price = 10
        self.size_attribute_m.default_extra_price = 5
        self.no_variant_attribute_second.default_extra_price = 0.5

        product_template = self.env['product.template'].create({
            'name': 'A dyn/alw/nev product',
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': self.dynamic_attribute.id,
            'value_ids': [Command.set([dyn1.id, dyn2.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.no_variant_attribute.id,
            'value_ids': [Command.set([self.no_variant_attribute_extra.id, self.no_variant_attribute_second.id])],
        }, {
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        }])

        # Create a variant (because of dynamic attribute)
        ptav_dyn2 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[0].id),
            ('product_attribute_value_id', '=', dyn2.id)
        ])
        ptav_never1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.no_variant_attribute_extra.id)
        ])
        ptav_always1 = self.env['product.template.attribute.value'].search([
            ('attribute_line_id', '=', product_template.attribute_line_ids[1].id),
            ('product_attribute_value_id', '=', self.size_attribute_s.id)
        ])

        self.env['product.product'].create({
            'available_in_pos': True,
            'product_tmpl_id': product_template.id,
            'product_template_attribute_value_ids': [(6, 0, (ptav_dyn2 + ptav_always1 + ptav_never1).ids)],
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_integration_dynamic_always_never_variant_price', login="pos_user")

    def test_image_variants_displayed(self):
        """
        Tests that the user can correctly chose variants in the product_configurator_popup
        if the variant was set as Image
        """
        image_attribute = self.env['product.attribute'].create({
            'name': 'Images',
            'display_type': 'image',
            'create_variant': 'always',
        })
        images = self.env['product.attribute.value'].create([{
            'name': 'First Image',
            'attribute_id': image_attribute.id,
        }, {
            'name': 'Second Image',
            'attribute_id': image_attribute.id,
            'default_extra_price': 20,
        }])
        product_template = self.env['product.template'].create({
            'name': 'Image Product',
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': image_attribute.id,
            'value_ids': [Command.set([images[0].id, images[1].id])],
        })

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_image_variants_displayed', login="pos_user")

    def test_variants_merge_line_barcode(self):
        """Tests the price of products with always variant when added to cart"""
        product_template = self.env['product.template'].create({
            'name': 'A variant product',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'is_storable': True,
            'taxes_id': False,
            'available_in_pos': True,
            'pos_categ_ids': [Command.set(self.pos_desk_misc_test.ids)],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.size_attribute.id,
            'value_ids': [Command.set([self.size_attribute_s.id, self.size_attribute_m.id])],
        })
        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [Command.set([self.color_attribute_blue.id])],
        })
        product_S_blue = self.env["product.product"].search([("product_tmpl_id", "=", product_template.id)])[0]
        self.assertEqual(len(product_S_blue.product_template_variant_value_ids), 1)  # Size S (only size varies)
        self.assertEqual(len(product_S_blue.product_template_attribute_value_ids), 2)  # Attributes: S, blue
        product_S_blue.barcode = "TEST123"

        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_variants_merge_line_barcode', login="pos_user")


from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosCashRounding(TestPointOfSaleHttpCommon):

    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.name = "AAAAAA"  # The POS only load the first 100 partners
        cls.cash_rounding_add_invoice_line = cls.env['account.cash.rounding'].create({
            'name': "cash_rounding_add_invoice_line",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })
        cls.cash_rounding_biggest_tax = cls.env['account.cash.rounding'].create({
            'name': "cash_rounding_biggest_tax",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'biggest_tax',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': "random_product",
            'available_in_pos': True,
            'list_price': 13.67,
            'taxes_id': [Command.set(cls.company_data['default_tax_sale'].ids)],
            'pos_categ_ids': [Command.set(cls.pos_desk_misc_test.ids)],
        })

    def test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.03,
                'amount_total': 15.7,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.03,
                'amount_total': -15.7,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.03,
                'amount_total': 15.7,
                'amount_paid': 15.72,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.03,
                'amount_total': 15.72,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.03,
                'amount_total': -15.7,
                'amount_paid': -15.72,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.03,
                'amount_total': 15.72,
            }])

    def test_cash_rounding_halfup_biggest_tax_only_round_cash_method(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.73,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.70,
                'amount_tax': 2.03,
                'amount_total': 15.73,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.73,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.70,
                'amount_tax': 2.03,
                'amount_total': 15.73,
            }])

    def test_archived_product_removed_and_order_is_refunded(self):
        """
        Tests that once product is archived after order is created
        product is not shown but the order can still be refunded.
        """
        self.env['pos.session'].sudo().search([('state', '!=', 'closed')]).write({'state': 'closed'})
        self.pos_admin.write({
            'group_ids': [
                (4, self.env.ref('product.group_product_manager').id),
                (4, self.env.ref('account.group_account_manager').id),
            ]
        })
        product = self.env['product.product'].create({
            'is_storable': True,
            'name': 'A Test Product',
            'available_in_pos': True,
            'list_price': 1,
        })

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_archived_product_removed_and_order_is_refunded_1",
            login="pos_admin",
        )

        # close session
        pos_session = self.main_pos_config.current_session_id
        pos_session.close_session_from_ui()
        product.action_archive()

        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_archived_product_removed_and_order_is_refunded_2",
            login="pos_admin",
        )
