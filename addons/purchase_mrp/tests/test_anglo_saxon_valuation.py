# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.fields import Command, Date, Datetime
from odoo.tools import mute_logger
from odoo.tests import Form, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data


@tagged('post_install', '-at_install')
class TestAngloSaxonValuationPurchaseMRP(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor01 = cls.env['res.partner'].create({'name': "Super Vendor"})

        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.stock_journal = _create_accounting_data(cls.env)
        cls.avco_category = cls.env['product.category'].create({
            'name': 'AVCO',
            'property_cost_method': 'average',
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_journal': cls.stock_journal.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
        })

        currency_grp = cls.env.ref('base.group_multi_currency')
        cls.env.user.write({'groups_id': [(4, currency_grp.id)]})

        cls.env.company.anglo_saxon_accounting = True

    def test_kit_anglo_saxo_price_diff(self):
        """
        Suppose an automated-AVCO configuration and a Price Difference Account defined on
        the product category. When buying a kit of that category at a higher price than its
        cost, the difference should be published on the Price Difference Account
        """
        kit, compo01, compo02 = self.env['product.product'].create([{
            'name': name,
            'standard_price': price,
            'is_storable': True,
            'categ_id': self.avco_category.id,
        } for name, price in [('Kit', 0), ('Compo 01', 10), ('Compo 02', 20)]])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': p.id,
                'product_qty': 1,
            }) for p in [compo01, compo02]]
        })
        kit.button_bom_cost()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor01
        with po_form.order_line.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100
        po = po_form.save()
        po.button_confirm()

        po.picking_ids.button_validate()

        action = po.action_create_invoice()
        invoice = self.env['account.move'].browse(action['res_id'])
        invoice.invoice_date = Date.today()
        invoice.action_post()

        svls = po.order_line.move_ids.stock_valuation_layer_ids
        self.assertEqual(len(svls), 2, "The invoice should have created two SVL (one by kit's component) for the price diff")
        self.assertEqual(sum(svls.mapped('value')), 100, "Should be the standard price of both components")

        input_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(sum(input_amls.mapped('balance')), 0)

    def test_buy_deliver_and_return_kit_with_auto_avco_components(self):
        """
        A kit K with two AVCO components
        - C01, cost share 25%
        - C02, cost share 75%
        K in Units
        C01, C02 in Litres
        Buy and receive 1 kit @ 100
        Deliver the kit
        Update the cost shares
        Return the delivery
        """
        stock_location = self.env['stock.location'].search([
            ('company_id', '=', self.env.company.id),
            ('name', '=', 'Stock'),
        ])
        customer_location = self.env.ref('stock.stock_location_customers')
        type_out = self.env['stock.picking.type'].search([
            ('company_id', '=', self.env.company.id),
            ('name', '=', 'Delivery Orders')])
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_litre = self.env.ref('uom.product_uom_litre')

        component01, component02 = self.env['product.product'].create([{
            'name': 'Component %s' % name,
            'is_storable': True,
            'categ_id': self.avco_category.id,
            'uom_id': uom_litre.id,
            'uom_po_id': uom_litre.id,
        } for name in ['01', '02']])

        kit = self.env['product.product'].create({
            'name': 'Super Kit',
            'type': 'consu',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        bom_kit = self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': component01.id,
                'product_qty': 1,
                'cost_share': 25,
            }), (0, 0, {
                'product_id': component02.id,
                'product_qty': 1,
                'cost_share': 75,
            })],
        })

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor01
        with po_form.order_line.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100
            pol_form.taxes_id.clear()
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_line_ids.quantity = 1
        receipt.button_validate()

        self.assertEqual(receipt.state, 'done')
        self.assertEqual(receipt.move_line_ids.product_id, component01 | component02)
        self.assertEqual(po.order_line.qty_received, 1)
        self.assertEqual(component01.stock_valuation_layer_ids.value, 25)
        self.assertEqual(component02.stock_valuation_layer_ids.value, 75)

        delivery = self.env['stock.picking'].create({
            'picking_type_id': type_out.id,
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'move_ids': [(0, 0, {
                'name': kit.name,
                'product_id': kit.id,
                'product_uom': kit.uom_id.id,
                'product_uom_qty': 1.0,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })],
        })
        delivery.action_confirm()
        delivery.move_ids.move_line_ids.quantity = 1
        delivery.button_validate()

        self.assertEqual(component01.stock_valuation_layer_ids.mapped('value'), [25, -25])
        self.assertEqual(component02.stock_valuation_layer_ids.mapped('value'), [75, -75])

        with mute_logger('odoo.tests.form.onchange'):
            with Form(bom_kit) as kit_form:
                with kit_form.bom_line_ids.edit(0) as line:
                    line.cost_share = 30
                with kit_form.bom_line_ids.edit(1) as line:
                    line.cost_share = 70

        wizard_form = Form(self.env['stock.return.picking'].with_context(active_id=delivery.id, active_model='stock.picking'))
        wizard = wizard_form.save()
        wizard.product_return_moves.quantity = 1
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        return_picking.move_ids.move_line_ids.quantity = 1
        return_picking.button_validate()

        self.assertEqual(component01.stock_valuation_layer_ids.mapped('value'), [25, -25, 25])
        self.assertEqual(component02.stock_valuation_layer_ids.mapped('value'), [75, -75, 75])

    def test_valuation_multicurrency_with_kits(self):
        """ Purchase a Kit in multi-currency and verify that the amount_currency is correctly computed.
        """

        # Setup Kit
        kit, cmp = self.env['product.product'].create([{
            'name': name,
            'standard_price': 0,
            'is_storable': True,
            'categ_id': self.avco_category.id,
        } for name in ['Kit', 'Cmp']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': cmp.id, 'product_qty': 5})]
        })

        # Setup Currency
        usd = self.env.ref('base.USD')
        eur = self.env.ref('base.EUR')
        self.env['res.currency.rate'].create({
            'name': Datetime.today(),
            'currency_id': usd.id,
            'rate': 1})
        self.env['res.currency.rate'].create({
            'name': Datetime.today(),
            'currency_id': eur.id,
            'rate': 2})

        # Create Purchase
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.vendor01
        po_form.currency_id = eur
        with po_form.order_line.new() as pol_form:
            pol_form.product_id = kit
            pol_form.price_unit = 100  # $50
        po = po_form.save()
        po.button_confirm()

        po.picking_ids.button_validate()

        svl = po.order_line.move_ids.stock_valuation_layer_ids.ensure_one()
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])

        self.assertEqual(svl.value, 50)  # USD
        self.assertEqual(input_aml.amount_currency, 100)  # EUR
        self.assertEqual(input_aml.balance, 50)  # USD

    def test_fifo_cost_adjust_mo_quantity(self):
        """ An MO using a FIFO cost method product as a component should not zero-out the std cost
        of the product if we unlock it once it is in a validated state and adjust the quantity of
        component used to be smaller than originally entered.
        """
        self.product_a.categ_id = self.env['product.category'].create({
            'name': 'FIFO',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time'
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'product_qty': 10,
                'price_unit': 100,
            })],
        })
        purchase_order.button_confirm()
        purchase_order.picking_ids[0].button_validate()

        manufacturing_order = self.env['mrp.production'].create({
            'product_id': self.product_b.id,
            'product_qty': 1,
            'move_raw_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'product_uom_qty': 100,
            })],
        })
        manufacturing_order.action_confirm()
        manufacturing_order.move_raw_ids.write({
            'quantity': 100,
            'picked': True,
        })
        manufacturing_order.button_mark_done()
        manufacturing_order.action_toggle_is_locked()
        manufacturing_order.move_raw_ids.quantity = 1

        self.assertEqual(self.product_a.standard_price, 100)

    def test_kit_valuation_no_pull(self):
        """ When selling a kit without ever moving it using a Pull rule, ensure that
        the invoice is generated with the correct COGS
        """

        if 'sale' not in self.env['ir.module.module']._installed():
            self.skipTest("Sale module is required for this test to run")

        # Prepare the cross-dock route (contains no Pull rules)
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.write({'reception_steps': 'two_steps', 'delivery_steps': 'pick_ship'})
        xdock_route = warehouse.crossdock_route_id

        # Prepare the kit
        kit_final_prod = self.product_a
        product_c = self.env['product.product'].create({
            'name': 'product_c',
            'lst_price': 120.0,
            'standard_price': 100.0,
            'property_account_income_id': self.copy_account(self.company_data['default_account_revenue']).id,
            'property_account_expense_id': self.copy_account(self.company_data['default_account_expense']).id,
            'taxes_id': [Command.set((self.tax_sale_a + self.tax_sale_b).ids)],
            'supplier_taxes_id': [Command.set((self.tax_purchase_a + self.tax_purchase_b).ids)]
        })
        kit_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': kit_final_prod.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
        })
        bom_line_b = Command.create({
            'product_id': self.product_b.id,
            'product_qty': 2,
        })
        bom_line_c = Command.create({
            'product_id': product_c.id,
            'product_qty': 1,
        })
        kit_bom.bom_line_ids = [
            bom_line_b,
            bom_line_c
        ]

        self.env['product.supplierinfo'].create({
            'product_id': self.product_b.id,
            'partner_id': self.partner_a.id,
            'price': 160,
        })
        self.env['product.supplierinfo'].create({
            'product_id': product_c.id,
            'partner_id': self.partner_a.id,
            'price': 100,
        })
        self.product_b.standard_price = 10
        (kit_final_prod + self.product_b + product_c).categ_id.write({
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        (kit_final_prod + self.product_b + product_c).is_storable = True

        # Create a sale order and use the cross dock route
        customer = self.env['res.partner'].create({'name': 'Test Customer'})
        so = self.env['sale.order'].create({
            'partner_id': customer.id,
            'order_line': [
                Command.create({
                    'name': self.product_a.name,
                    'product_id': self.product_a.id,
                    'product_uom_qty': 1,
                    'product_uom': self.product_a.uom_id.id,
                    'price_unit': 500,
                    'route_id': xdock_route.id,
                }),
            ],
        })
        so.action_confirm()
        po = so._get_purchase_orders()
        po.button_confirm()
        # The bom_line_ids on the stock moves should be set
        product_b_move = so.order_line.move_ids.filtered(lambda sm: sm.product_id == self.product_b)
        product_c_move = so.order_line.move_ids.filtered(lambda sm: sm.product_id == product_c)
        bom_line_b = kit_bom.bom_line_ids.filtered(lambda bl: bl.product_id == self.product_b)
        bom_line_c = kit_bom.bom_line_ids.filtered(lambda bl: bl.product_id == product_c)
        self.assertTrue(product_b_move.bom_line_id == bom_line_b, "The bom_line_id on the stock move was set incorrectly")
        self.assertTrue(product_c_move.bom_line_id == bom_line_c, "The bom_line_id on the stock move was set incorrectly")

        # Validate the chain
        receipt_move = po.picking_ids.move_ids
        receipt_move.write({'picked': True})
        receipt_move._action_done()

        cross_dock_move = receipt_move.move_dest_ids
        cross_dock_move.write({'picked': True})
        cross_dock_move._action_done()

        delivery_move = cross_dock_move.move_dest_ids
        delivery_move.write({'picked': True})
        delivery_move._action_done()

        self.assertTrue(so.order_line.qty_delivered == 1, "The Quantity Delivered on the Sale Order Line was not correctly calculated")

        account_move = so._create_invoices()
        account_move.action_post()

        # COGS == (160*2) + 100 = 420
        self.assertRecordValues(
            account_move.line_ids.sorted('balance'),
            [
                {'name': 'product_a',            'debit': 0.0, 'credit': 500},
                {'name': 'product_a',            'debit': 0.0, 'credit': 420},
                {'name': '15%',                  'debit': 0.0, 'credit': 75},
                {'name': 'product_a',            'debit': 420, 'credit': 0.0},
                {'name': f'{account_move.name}', 'debit': 575, 'credit': 0.0},
            ]
        )

    def test_avco_purchase_nested_kit_explode_cost_share(self):
        """
        Test the cost share calculation when purchasing a nested kit with several levels of BoMs

        Giga Kit:
            - C01, cost share 0%
            - Super Kit, cost share 100%:
                - C02, cost share 10%
                - Kit, cost share 60%:
                    - C02, cost share 25%
                    - C03, cost share 25%
                    - Sub Kit, cost share 50%
                        - C04, cost share 0%
                        - C05, cost share 0%
                - Sub Kit, cost share 20%
                    - C04, cost share 0%
                    - C05, cost share 0%
                - Phantom Kit, cost share 0%
                    - C05, cost share 100%
                - Triple Kit, cost share 10%
                    - C01, cost share 0%
                    - C02, cost share 0%
                    - C03, cost share 0% (Last line should round to reach 100%)
        Buy and receive 1 kit Giga Kit @ 1000
        """
        components = component01, component02, component03, component04, component05 = self.env['product.product'].create([{
            'name': 'Component %s' % name,
            'categ_id': self.avco_category.id,
        } for name in ('01', '02 ', '03', '04', '05')])

        giga_kit, super_kit, kit, sub_kit, phantom_kit, triple_kit = self.env['product.product'].create([{
            'name': name,
        } for name in ('Giga Kit', 'Super Kit', 'Kit', 'Sub Kit', 'Phantom Kit', 'Triple Kit')])

        self.env['mrp.bom'].create([{
            'product_tmpl_id': giga_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': component01.id, 'product_qty': 1, 'cost_share': 0}),
                Command.create({'product_id': super_kit.id, 'product_qty': 1, 'cost_share': 100}),
            ],
        }, {
            'product_tmpl_id': super_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': component02.id, 'product_qty': 1, 'cost_share': 10}),
                Command.create({'product_id': kit.id, 'product_qty': 1, 'cost_share': 60}),
                Command.create({'product_id': sub_kit.id, 'product_qty': 1, 'cost_share': 20}),
                Command.create({'product_id': phantom_kit.id, 'product_qty': 1, 'cost_share': 0}),
                Command.create({'product_id': triple_kit.id, 'product_qty': 1, 'cost_share': 10}),
            ],
        }, {
            'product_tmpl_id': kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': component02.id, 'product_qty': 1, 'cost_share': 25}),
                Command.create({'product_id': component03.id, 'product_qty': 1, 'cost_share': 25}),
                Command.create({'product_id': sub_kit.id, 'product_qty': 1, 'cost_share': 50}),
            ],
        }, {
            'product_tmpl_id': sub_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': component04.id, 'product_qty': 1, 'cost_share': 0}),
                Command.create({'product_id': component05.id, 'product_qty': 1, 'cost_share': 0}),
            ],
        }, {
            'product_tmpl_id': phantom_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': component05.id, 'product_qty': 1, 'cost_share': 100}),
            ],
        }, {
            'product_tmpl_id': triple_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': component01.id, 'product_qty': 1, 'cost_share': 0}),
                Command.create({'product_id': component02.id, 'product_qty': 1, 'cost_share': 0}),
                Command.create({'product_id': component03.id, 'product_qty': 1, 'cost_share': 0}),
            ],
        }])
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor01.id,
            'order_line': [
                Command.create({'product_id': super_kit.id, 'product_qty': 1, 'price_unit': 1000})
            ],
        })
        purchase_order.button_confirm()

        # Actual cost shares:
        # Component01:
        #   0 -> No stock valuation for that line
        #   1.0 * 0.1 * 0.333... (O%) = 0.0333... -> 3.33%
        # Component02:
        #   1.0 * 0.1  = 0.1 -> 10%
        #   1.0 * 0.6 * 0.25 = 0.15 -> 15%
        #   1.0 * 0.1 * 0.333... (O%) = 0.0333... -> 3.33%
        # Component03:
        #   1.0 * 0.6 * 0.25 = 0.15 -> 15%
        #   1.0 * 0.1 * 0.333... (O%) = 0.0333... -> 3.34% (last exploded line rounded)
        # Component04:
        #   1.0 * 0.6 * 0.5 * 0.5 (0%) = 0.15 -> 15%
        #   1.0 * 0.2 * 0.5 (0%) = 0.1 -> 10%
        # Component05:
        #   1.0 * 0.6 * 0.5 * 0.5 (0%) = 0.15 -> 15%
        #   1.0 * 0.2 * 0.5 (0%) = 0.1 -> 10%
        #   1.0 * 0.0 * 1.0 = 0.0 -> 0%
        self.assertEqual(sum(purchase_order.order_line.move_ids.mapped('cost_share')), 100.0)
        self.assertRecordValues(purchase_order.order_line.move_ids.sorted(lambda m: m.product_id.id), [
            {'product_id': component01.id, 'cost_share': 3.33},
            {'product_id': component02.id, 'cost_share': 10.0},
            {'product_id': component02.id, 'cost_share': 15.0},
            {'product_id': component02.id, 'cost_share': 3.33},
            {'product_id': component03.id, 'cost_share': 15.0},
            {'product_id': component03.id, 'cost_share': 3.34},
            {'product_id': component04.id, 'cost_share': 15.0},
            {'product_id': component04.id, 'cost_share': 10.0},
            {'product_id': component05.id, 'cost_share': 15.0},
            {'product_id': component05.id, 'cost_share': 10.0},
            {'product_id': component05.id, 'cost_share': 0.0},
        ])
        receipt = purchase_order.picking_ids
        receipt.button_validate()
        svls_ordered = components.stock_valuation_layer_ids.sorted(lambda l: l.product_id.id)
        self.assertRecordValues(svls_ordered, [
            {'product_id': component01.id},
            {'product_id': component02.id},
            {'product_id': component02.id},
            {'product_id': component02.id},
            {'product_id': component03.id},
            {'product_id': component03.id},
            {'product_id': component04.id},
            {'product_id': component04.id},
            {'product_id': component05.id},
            {'product_id': component05.id},
            {'product_id': component05.id},
        ])
        for svl, expected_unit_cost in zip(svls_ordered, [33.3, 100.0, 150.0, 33.3, 150.0, 33.4, 150.0, 100.0, 150.0, 100.0, 0.0]):
            self.assertAlmostEqual(svl.unit_cost, expected_unit_cost)

    def test_kit_bom_cost_share_constraint_with_variants(self):
        """
        Check that the cost share constraint is well behaved with respect to product attribute values:
        the sum of the cost share's of the bom of any product variant should either be 0% or 100%
        """
        attributes = self.env['product.attribute'].create([
            {'name': name} for name in ('Size', 'Color')
        ])
        attributes_values = ((attributes[0], ('S', 'M')), (attributes[1], ('Blue', 'Red')))
        self.env['product.attribute.value'].create([{
            'name': name,
            'attribute_id': attribute.id
        } for attribute, names in attributes_values for name in names])
        product_template = self.env['product.template'].create({
            'name': "lovely product",
            'is_storable': True,
        })
        size_attribute_lines, color_attribute_lines = self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': product_template.id,
            'attribute_id': attribute.id,
            'value_ids': [Command.set(attribute.value_ids.ids)]
        } for attribute in attributes])
        self.assertEqual(product_template.product_variant_count, 4)
        c1, c2, c3 = self.env['product.product'].create([
            {'name': f'Comp {i + 1}', 'categ_id': self.avco_category.id} for i in range(3)
        ])

        # Total cost share is 100% but in reality it is either 25% or 75% depending on the variant -> Invalid
        with self.assertRaises(UserError):
            self.env['mrp.bom'].create({
                'product_tmpl_id': product_template.id,
                'product_uom_id': product_template.uom_id.id,
                'product_qty': 1.0,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 25, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[0].id)]}),  # S size
                    Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 75, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[1].id)]}),  # M size
                ]
            })

        # The total cost share for Blue is 100% but for Red is 105% -> Invalid
        with self.assertRaises(UserError):
            self.env['mrp.bom'].create({
                'product_tmpl_id': product_template.id,
                'product_uom_id': product_template.uom_id.id,
                'product_qty': 1.0,
                'type': 'phantom',
                'bom_line_ids': [
                    Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 25, 'bom_product_template_attribute_value_ids': [Command.link(color_attribute_lines.product_template_value_ids[0].id)]}),  # Blue
                    Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 30, 'bom_product_template_attribute_value_ids': [Command.link(color_attribute_lines.product_template_value_ids[1].id)]}),  # Red
                    Command.create({'product_id': c3.id, 'product_qty': 1, 'cost_share': 75}),  # All attributes
                ]
            })

        # Check that optional lines (with a product_qty of 0) are ignored -> Valid
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': product_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 100}),  # All attributes
                Command.create({'product_id': c2.id, 'product_qty': 0, 'cost_share': 100}),  # All attributes - Qty 0 are Optional so the cost share should not impact the validation
            ]
        })

        # Variant with S attribute sum up to 100% others to 0% -> Valid
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': product_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 35, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[0].id)]}),  # S size
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 65, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[0].id)]}),  # S size
                Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 0}),  # All attributes
            ]
        })

        # All attribute values of a given attribute are equi-distributed -> Valid
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': product_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 30, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[0].id)]}),  # S
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 15, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[1].id)]}),  # M
                Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 15, 'bom_product_template_attribute_value_ids': [Command.link(size_attribute_lines.product_template_value_ids[1].id)]}),  # M
                Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 70}),  # All attributes
            ]
        })

        # Keep only the S Blue and the M Red variant
        product_template.product_variant_ids[1:3].action_archive()
        self.assertEqual(product_template.product_variant_count, 2)

        # Set up is fine for S Blue and M Red but fails for other non existing combination -> Valid
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': product_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 30, 'bom_product_template_attribute_value_ids': [
                    Command.link(size_attribute_lines.product_template_value_ids[0].id),  # S
                    Command.link(color_attribute_lines.product_template_value_ids[0].id),  # Blue
                ]}),  # S or Blue
                Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 30, 'bom_product_template_attribute_value_ids': [
                    Command.link(size_attribute_lines.product_template_value_ids[1].id),  # M
                    Command.link(color_attribute_lines.product_template_value_ids[1].id),  # Red
                ]}),  # M or Red
                Command.create({'product_id': c3.id, 'product_qty': 1, 'cost_share': 70}),  # All attributes
            ]
        })

    def test_kit_cost_share_variant_and_optional_lines(self):
        """
        Ensure the cost share is well computed when purchasing a kit with optional or variant specific lines
        """
        size_attribute = self.env['product.attribute'].create({'name': 'Size'})
        self.env['product.attribute.value'].create([{
            'name': name,
            'attribute_id': size_attribute.id
        } for name in ('S', 'M', 'L')])
        product_template = self.env['product.template'].create({
            'name': "Lovely product",
            'is_storable': True,
        })
        attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': product_template.id,
            'attribute_id': size_attribute.id,
            'value_ids': [Command.set(size_attribute.value_ids.ids)]
        })
        self.assertEqual(product_template.product_variant_count, 3)
        components = c1, c2, c3, c4, c5, c6 = self.env['product.product'].create([
            {
                'name': f'Comp {i + 1}',
                'categ_id': self.avco_category.id,
            } for i in range(6)
        ])
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': product_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': c1.id, 'product_qty': 1, 'cost_share': 25, 'bom_product_template_attribute_value_ids': [Command.link(attribute_lines[0].product_template_value_ids[0].id)]}),  # S size
                Command.create({'product_id': c2.id, 'product_qty': 1, 'cost_share': 75, 'bom_product_template_attribute_value_ids': [Command.link(attribute_lines[0].product_template_value_ids[0].id)]}),  # S size
                Command.create({'product_id': c3.id, 'product_qty': 1, 'cost_share': 100, 'bom_product_template_attribute_value_ids': [Command.link(attribute_lines[0].product_template_value_ids[1].id)]}),  # M size
                Command.create({'product_id': c4.id, 'product_qty': 1, 'cost_share': 0, 'bom_product_template_attribute_value_ids': [Command.link(attribute_lines[0].product_template_value_ids[2].id)]}),  # L sizes
                Command.create({'product_id': c5.id, 'product_qty': 1, 'cost_share': 0}),  # All sizes
                Command.create({'product_id': c6.id, 'product_qty': 0, 'cost_share': 100}),  # All sizes
            ]
        })
        # Purchase one variant for each sizes
        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor01.id,
            'order_line': [
                Command.create({'product_id': variant.id, 'product_qty': 1, 'price_unit': 1000}) for variant in product_template.product_variant_ids
            ],
        })
        purchase_order.button_confirm()

        self.assertEqual(sum(purchase_order.order_line.move_ids.mapped('cost_share')), 300.0, 'There are 3 lines and each line should be associated with a total cost_share of 100%')
        self.assertRecordValues(purchase_order.order_line.move_ids.sorted(lambda m: m.product_id.id), [
            {'product_id': c1.id, 'cost_share': 25.0},
            {'product_id': c2.id, 'cost_share': 75.0},
            {'product_id': c3.id, 'cost_share': 100.0},
            {'product_id': c4.id, 'cost_share': 50.0},
            {'product_id': c5.id, 'cost_share': 0.0},
            {'product_id': c5.id, 'cost_share': 0.0},
            {'product_id': c5.id, 'cost_share': 50.0},
            {'product_id': c6.id, 'cost_share': 0.0},
            {'product_id': c6.id, 'cost_share': 0.0},
            {'product_id': c6.id, 'cost_share': 0.0},
        ])

        receipt = purchase_order.picking_ids
        receipt.button_validate()

        self.assertRecordValues(components.stock_valuation_layer_ids.sorted('id'), [
            # S attribute
            {'product_id': c1.id, 'unit_cost':  250.0},
            {'product_id': c2.id, 'unit_cost':  750.0},
            {'product_id': c5.id, 'unit_cost':  0.0},

            # M attribute
            {'product_id': c3.id, 'unit_cost': 1000.0},
            {'product_id': c5.id, 'unit_cost':  0.0},

            # L attribute - Cost share 0% automatically splitted
            {'product_id': c4.id, 'unit_cost':  500.0},
            {'product_id': c5.id, 'unit_cost':  500.0},
        ])
