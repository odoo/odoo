from unittest import skip

import odoo

from odoo.addons.pos_mrp.tests.common import CommonPosMrpTest
from odoo import Command, fields


@odoo.tests.tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
class TestPosMrp(CommonPosMrpTest):
    def test_bom_kit_order_total_cost(self):
        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': self.product_product_kit_one.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        self.assertEqual(order.lines[0].total_cost, 10.0)

    def test_bom_kit_with_kit_invoice_valuation(self):
        self.product_product_kit_one.categ_id = self.category_fifo_realtime
        self.product_product_kit_two.categ_id = self.category_fifo_realtime
        self.product_product_kit_three.categ_id = self.category_fifo_realtime
        self.product_product_kit_four.categ_id = self.category_fifo_realtime

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'to_invoice': True,
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.product_product_kit_three.id},
                {'product_id': self.product_product_kit_four.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.assertEqual(order.lines.filtered(
            lambda l: l.product_id == self.product_product_kit_three).total_cost, 30.0)
        accounts = self.product_product_kit_three.product_tmpl_id.get_product_accounts()
        debit_interim_account = accounts['stock_output']
        credit_expense_account = accounts['expense']
        invoice_accounts = order.account_move.line_ids.mapped('account_id.id')
        self.assertTrue(debit_interim_account.id in invoice_accounts)
        self.assertTrue(credit_expense_account.id in invoice_accounts)
        expense_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == credit_expense_account.id)
        self.assertEqual(expense_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).credit, 0.0)
        self.assertEqual(expense_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).debit, 30.0)
        interim_line = order.account_move.line_ids.filtered(lambda l: l.account_id.id == debit_interim_account.id)
        self.assertEqual(interim_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).credit, 30.0)
        self.assertEqual(interim_line.filtered(
            lambda l: l.product_id == self.product_product_kit_three).debit, 0.0)
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()

    def test_bom_kit_different_uom_invoice_valuation(self):
        """This test make sure that when a kit is made of product using UoM A but the bom line uses UoM B
           the price unit is correctly computed on the invoice lines.
        """
        self.env.user.group_ids += self.env.ref('uom.group_uom')

        # Edit kit product and component product
        self.product_product_kit_one.categ_id = self.category_fifo_realtime
        self.product_product_comp_one.standard_price = 12000
        self.product_product_comp_one.uom_id = self.env.ref('uom.product_uom_dozen').id

        # Edit kit product quantity
        self.bom_one_line.bom_line_ids[0].product_qty = 6.0
        self.bom_one_line.bom_line_ids[0].product_uom_id = self.env.ref('uom.product_uom_unit').id
        self.bom_one_line.product_qty = 2.0

        order, _ = self.create_backend_pos_order({
            'order_data': {
                'to_invoice': True,
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.product_product_kit_one.id, 'qty': 2},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        accounts = self.product_product_kit_one.product_tmpl_id.get_product_accounts()
        expense_line = order.account_move.line_ids.filtered(
            lambda l: l.account_id.id == accounts['expense'].id)
        interim_line = order.account_move.line_ids.filtered(
            lambda l: l.account_id.id == accounts['stock_output'].id)
        expense_line = expense_line.filtered(lambda l: l.product_id == self.product_product_kit_one)
        interim_line = interim_line.filtered(lambda l: l.product_id == self.product_product_kit_one)

        self.assertEqual(expense_line.debit, 6000.0)
        self.assertEqual(interim_line.credit, 6000.0)

    def test_bom_kit_order_total_cost_with_shared_component(self):
        self.bom_one_line.product_tmpl_id.categ_id = self.category_average
        self.bom_two_lines.product_tmpl_id.categ_id = self.category_average
        kit_1 = self.bom_one_line.product_tmpl_id.product_variant_id
        kit_2 = self.bom_two_lines.product_tmpl_id.product_variant_id

        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': kit_1.id},
                {'product_id': kit_2.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        self.assertRecordValues(order.lines, [
            {'product_id': kit_1.id, 'total_cost': 10.0},
            {'product_id': kit_2.id, 'total_cost': 20.0},
        ])

    def test_bom_nested_kit_order_total_cost_with_shared_component(self):
        self.bom_one_line.product_tmpl_id.categ_id = self.category_average
        self.bom_two_lines.product_tmpl_id.categ_id = self.category_average
        self.ten_dollars_with_5_incl.standard_price = 30.0
        self.twenty_dollars_with_5_incl.standard_price = 50.0
        kit_1 = self.bom_one_line.copy()
        kit_2 = self.bom_one_line.copy()
        kit_2.product_tmpl_id = self.ten_dollars_with_5_incl
        kit_3 = self.bom_one_line.copy()
        kit_3.product_tmpl_id = self.twenty_dollars_with_5_incl
        kit_3.bom_line_ids[0].product_id = kit_1.product_tmpl_id.product_variant_id

        order, _ = self.create_backend_pos_order({
            'line_data': [
                {'product_id': kit_3.product_tmpl_id.product_variant_id.id},
                {'product_id': kit_2.product_tmpl_id.product_variant_id.id}
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        self.assertRecordValues(order.lines, [
            {'product_id': kit_3.product_tmpl_id.product_variant_id.id, 'total_cost': 50.0},
            {'product_id': kit_2.product_tmpl_id.product_variant_id.id, 'total_cost': 30.0},
        ])

    def test_never_variant_bom_product_picking(self):
        self.attribute_1 = self.env['product.attribute'].create({
            'name': 'Color',
            'create_variant': 'no_variant',
            'sequence': 1,
        })

        # Create attribute values
        self.value_1_1 = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': self.attribute_1.id,
            'sequence': 1,
        })
        self.value_1_2 = self.env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': self.attribute_1.id,
            'sequence': 2,
        })

        # Create the configurable product with attributes
        self.configurable_product = self.env['product.product'].create({
            'name': 'Configurable Chair',
            'is_storable': True,
            'available_in_pos': True,
            'list_price': 100,
        })

        ptal = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': self.configurable_product.product_tmpl_id.id,
            'attribute_id': self.attribute_1.id,
            'value_ids': [Command.set([self.value_1_1.id, self.value_1_2.id])],
        }])

        # Create the component products
        self.component_common = self.env['product.product'].create({
            'name': 'Common Frame',
            'is_storable': True,
            'list_price': 50,
        })

        self.component_red = self.env['product.product'].create({
            'name': 'Red Cushion',
            'is_storable': True,
            'list_price': 20,
        })

        self.component_blue = self.env['product.product'].create({
            'name': 'Blue Cushion',
            'is_storable': True,
            'list_price': 20,
        })

        # Create BOM for the configurable product
        self.bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.configurable_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',  # Kit type
            'bom_line_ids': [
                Command.create({
                    'product_id': self.component_common.id,
                    'product_qty': 1.0,
                }),
                Command.create({
                    'product_id': self.component_red.id,
                    'product_qty': 1.0,
                    'bom_product_template_attribute_value_ids': [
                        Command.link(self.configurable_product.product_tmpl_id.attribute_line_ids[0].product_template_value_ids[0].id)
                    ],
                }),
                Command.create({
                    'product_id': self.component_blue.id,
                    'product_qty': 1.0,
                    'bom_product_template_attribute_value_ids': [
                        Command.link(self.configurable_product.product_tmpl_id.attribute_line_ids[0].product_template_value_ids[1].id)
                    ],
                }),
            ],
        })
        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id
        pos_order_data = {
                'amount_paid': 100,
                'amount_return': 0,
                'amount_tax': 0,
                'amount_total': 100,
                'date_order': fields.Datetime.to_string(fields.Datetime.now()),
                'fiscal_position_id': False,
                'lines': [
                    Command.create({
                        'attribute_value_ids': [ptal.product_template_value_ids[0].id],
                        'discount': 0,
                        'pack_lot_ids': [],
                        'price_unit': 100.0,
                        'product_id': self.configurable_product.id,
                        'price_subtotal': 100.0,
                        'price_subtotal_incl': 100.0,
                        'qty': 1,
                        'tax_ids': [],
                    }),
                    Command.create({
                        'attribute_value_ids': [ptal.product_template_value_ids[1].id],
                        'discount': 0,
                        'pack_lot_ids': [],
                        'price_unit': 100.0,
                        'product_id': self.configurable_product.id,
                        'price_subtotal': 100.0,
                        'price_subtotal_incl': 100.0,
                        'qty': 1,
                        'tax_ids': [],
                        }),
                ],
                'name': 'Order 12345-123-1234',
                'partner_id': False,
                'session_id': current_session.id,
                'sequence_number': 2,
                'payment_ids': [
                    Command.create({
                        'amount': 100,
                        'name': fields.Datetime.now(),
                        'payment_method_id': self.cash_payment_method.id
                    })
                ],
                'uuid': '12345-123-1234',
                'last_order_preparation_change': '{}',
                'user_id': self.env.uid
            }
        self.env['pos.order'].sync_from_ui([pos_order_data])['pos.order'][0]['id']
        self.assertEqual(len(current_session.picking_ids.move_line_ids), 4)

    def test_bom_variant_exclusive_bom_lines(self):
        """This test make sure that the cost is correctly computed when a product has a BoM with lines linked
              to specific variant."""
        category = self.env['product.category'].create({
            'name': 'Category for kit',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        attribute_size = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
            'value_ids': [Command.create({'name': 'S'}), Command.create({'name': 'L'})],
        })
        product_test = self.env['product.template'].create({
            'name': 'Test product',
            'categ_id': category.id,
            'is_storable': True,
            'available_in_pos': True,
            'attribute_line_ids': [Command.create({
                'attribute_id': attribute_size.id,
                'value_ids': [Command.set(attribute_size.value_ids.ids)],
            })],
        })

        component_size = self.env['product.product'].create({
            'name': 'Test Product - Small',
            'standard_price': 10.0,
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': product_test.id,
            'product_uom_id': product_test.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': component_size.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': product_test.product_variant_ids[0].product_template_variant_value_ids.ids
                    }),
                Command.create({
                    'product_id': component_size.id,
                    'product_qty': 2,
                    'bom_product_template_attribute_value_ids': product_test.product_variant_ids[1].product_template_variant_value_ids.ids
                    }),
            ]
        })
        product_1 = product_test.product_variant_ids[0]
        product_2 = product_test.product_variant_ids[1]
        self.pos_config_usd.open_ui()
        order = self.env['pos.order'].create({
            'session_id': self.pos_config_usd.current_session_id.id,
            'lines': [(0, 0, {
                'name': product_2.name,
                'product_id': product_2.id,
                'price_unit': product_2.lst_price,
                'qty': 1,
                'tax_ids': [],
                'price_subtotal': product_2.lst_price,
                'price_subtotal_incl': product_2.lst_price,
            }),
            (0, 0, {
                'name': product_1.name,
                'product_id': product_1.id,
                'price_unit': product_1.lst_price,
                'qty': 1,
                'tax_ids': [],
                'price_subtotal': product_1.lst_price,
                'price_subtotal_incl': product_1.lst_price,
            })],
            'pricelist_id': self.pos_config_usd.pricelist_id.id,
            'amount_paid': product_2.lst_price + product_1.lst_price,
            'amount_total': product_2.lst_price + product_1.lst_price,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
        })
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.pos_config_usd.current_session_id.action_pos_session_closing_control()
        self.assertRecordValues(order.lines, [
            {'product_id': product_2.id, 'total_cost': 20},
            {'product_id': product_1.id, 'total_cost': 10},
        ])


# TODO : Merge this test with the other class when it is not skipped anymore
@odoo.tests.tagged('post_install', '-at_install')
class TestPosMrpTemp(CommonPosMrpTest):
    def test_bom_kit_different_uom_invoice_valuation_no_invoice(self):
        """This test make sure that when a kit is made of product using UoM A but the bom line uses UoM B
           the price unit is correctly computed on the invoice lines.
        """
        self.env.user.group_ids += self.env.ref('uom.group_uom')
        self.env.company.inventory_valuation = 'real_time'
        # Edit kit product and component product
        self.product_product_kit_one.categ_id = self.category_fifo_realtime
        self.product_product_comp_one.standard_price = 12000
        self.product_product_comp_one.uom_id = self.env.ref('uom.product_uom_dozen').id
        self.product_product_comp_one.categ_id = self.category_fifo_realtime
        self.product_product_comp_one.is_storable = True

        # Edit kit product UoM
        self.bom_one_line.bom_line_ids[0].product_uom_id = self.env.ref('uom.product_uom_unit').id

        self.create_backend_pos_order({
            'order_data': {
                'partner_id': self.partner_moda.id,
            },
            'line_data': [
                {'product_id': self.product_product_kit_one.id, 'qty': 1},
            ],
            'payment_data': [
                {'payment_method_id': self.cash_payment_method.id}
            ]
        })

        current_session = self.pos_config_usd.current_session_id
        current_session.action_pos_session_closing_control()

        accounts = self.product_product_kit_one.product_tmpl_id.get_product_accounts()
        expense_line = current_session.move_id.line_ids.filtered(
            lambda l: l.account_id.id == accounts['expense'].id)
        interim_line = current_session.move_id.line_ids.filtered(
            lambda l: l.account_id.id == accounts['stock_valuation'].id)

        self.assertEqual(expense_line.debit, 1000.0)
        self.assertEqual(interim_line.credit, 1000.0)
