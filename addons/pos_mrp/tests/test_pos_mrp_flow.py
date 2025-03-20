# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosMrp(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.env.user.group_ids += self.env.ref('mrp.group_mrp_manager')
        category = self.env['product.category'].create({
            'name': 'Category for kit',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })

        # Create Awesome Kit with 2 awesome items
        self.awesome_kit = self.env['product.product'].create({
            'name': 'Kit Product',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': category.id,
        })
        self.product_awesome_item.product_variant_id.write({
            'is_storable': True,
            'lst_price': 10.0,
            'standard_price': 5.0,
        })
        self.product_awesome_article.product_variant_id.write({
            'is_storable': True,
            'lst_price': 10.0,
            'standard_price': 10.0,
        })
        self.awesome_bom = self.env['mrp.bom'].create({
            'product_id': self.awesome_kit.id,
            'product_tmpl_id': self.awesome_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_awesome_item.product_variant_id.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.product_awesome_article.product_variant_id.id, 'product_qty': 1})
            ],
        })

        # Create Quality Kit with 1 quality item
        self.quality_kit = self.env['product.product'].create({
            'name': 'Quality Kit',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': category.id,
        })
        self.product_quality_item.product_variant_id.write({
            'is_storable': True,
            'lst_price': 10.0,
            'standard_price': 5.0,
        })
        self.quality_bom = self.env['mrp.bom'].create({
            'product_id': self.quality_kit.id,
            'product_tmpl_id': self.quality_kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_quality_item.product_variant_id.id, 'product_qty': 1}),
            ],
        })

        # Create Kit of kits with 1 awesome kit and 1 quality kit
        self.kit_of_kits = self.env['product.product'].create({
            'name': 'Kit of Kits',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': category.id,
        })
        self.kit_of_kits_bom = self.env['mrp.bom'].create({
            'product_id': self.kit_of_kits.id,
            'product_tmpl_id': self.kit_of_kits.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.awesome_kit.id, 'product_qty': 1}),
                (0, 0, {'product_id': self.quality_kit.id, 'product_qty': 1}),
            ],
        })

        # Create kit of kits with 2 awesome kits
        self.kit_of_kits_2 = self.env['product.product'].create({
            'name': 'Kit of Kits 2',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': category.id,
        })
        self.kit_of_kits_2_bom = self.env['mrp.bom'].create({
            'product_id': self.kit_of_kits_2.id,
            'product_tmpl_id': self.kit_of_kits_2.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.awesome_kit.id, 'product_qty': 2}),
            ],
        })

    def test_bom_kit_order_total_cost(self):
        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': self.awesome_kit, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 10.0},
        ])
        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.assertEqual(order.lines[0].total_cost, 15.0)

    def test_bom_kit_with_kit_invoice_valuation(self):
        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': self.kit_of_kits, 'qty': 1, 'discount': 0},
            {'product_id': self.kit_of_kits_2, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 20.0},
        ], False, False, self.partner_one, True)
        self.close_session()

        self.assertEqual(order.lines.filtered(lambda l: l.product_id.id == self.kit_of_kits.id).total_cost, 20.0)
        self.assertEqual(order.lines.filtered(lambda l: l.product_id.id == self.kit_of_kits_2.id).total_cost, 30.0)
        accounts = self.kit_of_kits.product_tmpl_id.get_product_accounts()
        debit_interim_account = accounts['stock_output']
        credit_expense_account = accounts['expense']
        invoice_accounts = order.account_move.line_ids.mapped('account_id.id')
        self.assertTrue(debit_interim_account.id in invoice_accounts)
        self.assertTrue(credit_expense_account.id in invoice_accounts)
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == credit_expense_account.id)
        self.assertEqual(expense_line.filtered(lambda l: l.product_id.id == self.kit_of_kits.id).credit, 0.0)
        self.assertEqual(expense_line.filtered(lambda l: l.product_id.id == self.kit_of_kits.id).debit, 20.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == debit_interim_account.id)
        self.assertEqual(interim_line.filtered(lambda l: l.product_id.id == self.kit_of_kits_2.id).credit, 30.0)
        self.assertEqual(interim_line.filtered(lambda l: l.product_id.id == self.kit_of_kits_2.id).debit, 0.0)

    def test_bom_kit_different_uom_invoice_valuation(self):
        """This test make sure that when a kit is made of product using UoM A but the bom line uses UoM B
           the price unit is correctly computed on the invoice lines.
        """
        self.env.user.group_ids += self.env.ref('uom.group_uom')
        self.awesome_bom.bom_line_ids[1].unlink()
        self.awesome_bom.write({
            'product_qty': 2.0,
        })
        self.awesome_kit.bom_line_ids[0].write({
            'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            'product_qty': 6.0,
        })
        self.awesome_kit.write({
            'lst_price': 2.0,
        })
        self.product_awesome_item.write({
            'standard_price': 12000.0,
            'taxes_id': False,
            'uom_id': self.env.ref('uom.product_uom_dozen').id,
        })

        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': self.awesome_kit, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 2.0},
        ], False, False, self.partner_one, True)

        accounts = self.awesome_kit.product_tmpl_id.get_product_accounts()
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == accounts['expense'].id)
        self.assertEqual(expense_line.filtered(lambda l: l.product_id == self.awesome_kit).debit, 6000.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == accounts['stock_output'].id)
        self.assertEqual(interim_line.filtered(lambda l: l.product_id == self.awesome_kit).credit, 6000.0)

    def test_bom_kit_order_total_cost_with_shared_component(self):
        category = self.env['product.category'].create({
            'name': 'Category for average cost',
            'property_cost_method': 'average',
        })

        self.awesome_kit.write({
            'categ_id': category.id,
            'lst_price': 30.0,
            'type': 'consu',
        })
        self.quality_kit.write({
            'categ_id': category.id,
            'lst_price': 200.0,
            'type': 'consu',
        })
        self.product_awesome_item.product_variant_id.write({
            'lst_price': 10.0,
            'standard_price': 5.0,
        })
        self.quality_bom.bom_line_ids = [(0, 0, {
            'product_id': self.product_awesome_item.product_variant_id.id,
            'product_qty': 1.0,
        })]
        self.product_awesome_article.product_variant_id.write({
            'lst_price': 20.0,
            'standard_price': 10.0,
        })
        self.product_quality_item.product_variant_id.write({
            'lst_price': 30.0,
            'standard_price': 20.0,
        })
        self.quality_bom.bom_line_ids[0].product_qty = 5
        self.quality_bom.bom_line_ids[1].product_qty = 10

        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': self.quality_kit, 'qty': 1, 'discount': 0},
            {'product_id': self.awesome_kit, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 230.0},
        ])

        self.pos_config.current_session_id.action_pos_session_closing_control()
        self.assertRecordValues(order.lines, [
            {'product_id': self.quality_kit.id, 'total_cost': 150.0},
            {'product_id': self.awesome_kit.id, 'total_cost': 15.0},
        ])

    def test_bom_nested_kit_order_total_cost_with_shared_component(self):
        category = self.env['product.category'].create({
            'name': 'Category for average cost',
            'property_cost_method': 'average',
        })

        self.awesome_kit.write({
            'categ_id': category.id,
            'lst_price': 30.0,
            'type': 'consu',
        })
        self.quality_kit.write({
            'categ_id': category.id,
            'lst_price': 200.0,
            'type': 'consu',
        })
        kit_3 = self.env['product.product'].create({
            'name': 'Kit Product 3',
            'available_in_pos': True,
            'is_storable': True,
            'lst_price': 200.0,
            'categ_id': category.id,
        })

        self.product_awesome_item.product_variant_id.write({
            'lst_price': 10.0,
            'standard_price': 100,
        })
        self.awesome_bom.bom_line_ids = [(5, 0)]
        self.awesome_bom.bom_line_ids = [(0, 0, {
            'product_id': self.product_awesome_item.product_variant_id.id,
            'product_qty': 1
        })]
        self.quality_bom.bom_line_ids = [(5, 0)]
        self.quality_bom.bom_line_ids = [(0, 0, {
            'product_id': self.product_awesome_item.product_variant_id.id,
            'product_qty': 1
        })]

        self.env['mrp.bom'].create({
            'product_id': kit_3.id,
            'product_tmpl_id': kit_3.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': self.awesome_kit.id, 'product_qty': 1}),
            ],
        })

        self.pos_config.open_ui()
        order = self.create_order([
            {'product_id': kit_3, 'qty': 1, 'discount': 0},
            {'product_id': self.quality_kit, 'qty': 1, 'discount': 0},
        ], [
            {'payment_method_id': self.bank_payment_method, 'amount': 430.0},
        ])

        self.assertRecordValues(order.lines, [
            {'product_id': kit_3.id, 'total_cost': 100.0},
            {'product_id': self.quality_kit.id, 'total_cost': 100.0},
        ])
