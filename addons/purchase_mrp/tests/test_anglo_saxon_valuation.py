# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

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

        cls.stock_input_account, cls.stock_output_account, cls.stock_valuation_account, cls.expense_account, cls.income_account, cls.stock_journal = _create_accounting_data(cls.env)
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
        cls.env.user.write({'group_ids': [(4, currency_grp.id)]})

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
        } for name in ['01', '02']])

        kit = self.env['product.product'].create({
            'name': 'Super Kit',
            'type': 'consu',
            'uom_id': uom_unit.id,
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
            pol_form.tax_ids.clear()
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

    def test_purchase_kit_cumulative_cost_share_with_auto_avco_components_bom_repetition(self):
        """
        A kit Super Kit with three AVCO components
        - C01, cost share 10%
        - A kit Sub Kit 1 with three AVCO components, cost share 30%
            - C02, cost share 50%
            - C03, cost share 25%
            - Sub Kit 2 with two AVCO components, cost share 25%
                - C04, cost share 30%
                - C05, cost share 70%
        - Sub Kit 2 with two AVCO components, cost share 60%
                - C04, cost share 30%
                - C05, cost share 70%
        Buy and receive 1 kit Super Kit @ 1000
        """
        component01, component02, component03, component04, component05 = self.env['product.product'].create([{
            'name': 'Component %s' % name,
            'categ_id': self.avco_category.id,
        } for name in ['01 (super kit)', '02 (sub kit 1)', '03 (sub kit 1)', '04 (sub kit 2)', '05 (sub kit 2)']])

        super_kit, sub_kit_1, sub_kit_2 = self.env['product.product'].create([{
            'name': name,
        } for name in ['Super Kit', 'Sub Kit 1', 'Sub Kit 2']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': super_kit.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component01.id,
                'product_qty': 1,
                'cost_share': 10,
            }), Command.create({
                'product_id': sub_kit_1.id,
                'product_qty': 1,
                'cost_share': 30,
            }), Command.create({
                'product_id': sub_kit_2.id,
                'product_qty': 1,
                'cost_share': 60,
            })],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': sub_kit_1.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component02.id,
                'product_qty': 1,
                'cost_share': 50,
            }), Command.create({
                'product_id': component03.id,
                'product_qty': 1,
                'cost_share': 25,
            }), Command.create({
                'product_id': sub_kit_2.id,
                'product_qty': 1,
                'cost_share': 25,
            })],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': sub_kit_2.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component04.id,
                'product_qty': 1,
                'cost_share': 30,
            }), Command.create({
                'product_id': component05.id,
                'product_qty': 1,
                'cost_share': 70,
            })],
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor01.id,
            'order_line': [Command.create({
                'product_id': super_kit.id,
                'product_qty': 1,
                'price_unit': 1000,
                'tax_ids': [Command.clear()],
            })],
        })
        purchase_order.button_confirm()

        receipt = purchase_order.picking_ids
        receipt.button_validate()

        # Actual cost shares:
        # Component01:
        #   0.1
        # Component02:
        #   0.3 * 0.5  = 0.15
        # Component03:
        #   0.3 * 0.25 = 0.075 -> 0.08
        # Component04:
        #   0.6 * 0.3 = 0.18
        #   0.3 * 0.25 * 0.3 = 0.0225 -> 0.02
        # Component05:
        #   0.6 * 0.7 = 0.42
        #   0.3 * 0.25 * 0.7 = 0.0525 -> 0.05
        # => 0.1 + 0.15 + 0.08 + 0.02 + 0.18 + 0.05 + 0.42 = 1.0
        self.assertRecordValues(component01.stock_valuation_layer_ids, [{'value': 100.0,   'unit_cost': 100.0,    'quantity': 1.0}])
        self.assertRecordValues(component02.stock_valuation_layer_ids, [{'value': 150.0,   'unit_cost': 150.0,    'quantity': 1.0}])
        self.assertRecordValues(component03.stock_valuation_layer_ids, [{'value':  80.0,   'unit_cost':  80.0,    'quantity': 1.0}])
        self.assertRecordValues(
            component04.stock_valuation_layer_ids,
            [
                {'value':  20,   'unit_cost':  20,   'quantity': 1.0},
                {'value': 180,   'unit_cost': 180,   'quantity': 1.0},
            ]
        )
        self.assertRecordValues(
            component05.stock_valuation_layer_ids,
            [
                {'value':  50,    'unit_cost': 50,   'quantity': 1.0},
                {'value': 420,   'unit_cost': 420,   'quantity': 1.0},
            ]
        )

    def test_purchase_kit_cost_share_0_with_auto_avco_components(self):
        """
        If a BoM has BoM lines with cost shares that add to 0 (i.e., each one has cost share of 0)
        then we should distribute the cost share equally among all of them. Otherwise, any lines
        with a cost share of 0 should be valuated as 0.

        A kit A with two AVCO components
        - C01, cost share 100%
        - C02, cost share 0%
        A kit B with two AVCO components
        - C03, cost share 0%
        - C04, cost share 0%
        """
        component01, component02, component03, component04 = self.env['product.product'].create([{
            'name': 'Component %s' % name,
            'categ_id': self.avco_category.id,
        } for name in ['01', '02', '03', '04']])

        kit_a, kit_b = self.env['product.product'].create([{
            'name': name,
            'type': 'consu',
        } for name in ['Kit A', 'Kit B']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit_a.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component01.id,
                'product_qty': 1,
                'cost_share': 100,
            }), Command.create({
                'product_id': component02.id,
                'product_qty': 1,
                'cost_share': 0,
            })],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit_b.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component03.id,
                'product_qty': 1,
                'cost_share': 0,
            }), Command.create({
                'product_id': component04.id,
                'product_qty': 1,
                'cost_share': 0,
            })],
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor01.id,
            'order_line': [Command.create({
                'product_id': kit_a.id,
                'product_qty': 1,
                'price_unit': 1000,
                'tax_ids': [Command.clear()],
            }), Command.create({
                'product_id': kit_b.id,
                'product_qty': 1,
                'price_unit': 1000,
                'tax_ids': [Command.clear()],
            })],
        })
        purchase_order.button_confirm()
        receipt = purchase_order.picking_ids
        receipt.button_validate()

        self.assertRecordValues(component01.stock_valuation_layer_ids, [{'value': 1000.0,   'unit_cost': 1000.0,   'quantity': 1.0}])
        self.assertRecordValues(component02.stock_valuation_layer_ids, [{'value': 0.0,      'unit_cost': 0.0,      'quantity': 1.0}])
        self.assertRecordValues(component03.stock_valuation_layer_ids, [{'value': 500.0,    'unit_cost': 500.0,    'quantity': 1.0}])
        self.assertRecordValues(component04.stock_valuation_layer_ids, [{'value': 500.0,    'unit_cost': 500.0,    'quantity': 1.0}])

    def test_purchase_kit_cost_share_0_with_auto_avco_components_bom_repetition(self):
        """
        If a BoM has BoM lines with cost shares that add to 0 (i.e., each one has cost share of 0)
        then we should distribute the cost share equally among all of them. Otherwise, any lines
        with a cost share of 0 should be valuated as 0.

        A kit A with two AVCO components
        - C01, cost share 0% -> 0.5
        - A Sub kit B with two AVCO components cost share 0% -> 0.5
            - C02, cost share 0% -> 0.1666666
            - C03, cost share 0% -> 0.1666666
            - C04, cost share 0% -> 0.1666666
        """
        component01, component02, component03, component04 = self.env['product.product'].create([{
            'name': 'Component %s' % name,
            'categ_id': self.avco_category.id,
        } for name in ['01', '02', '03', '04']])

        kit_a, kit_b = self.env['product.product'].create([{
            'name': name,
            'type': 'consu',
        } for name in ['Kit A', 'Kit B']])

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit_a.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component01.id,
                'product_qty': 1,
                'cost_share': 0,
            }), Command.create({
                'product_id': kit_b.id,
                'product_qty': 1,
                'cost_share': 0,
            })],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit_b.product_tmpl_id.id,
            'type': 'phantom',
            'bom_line_ids': [Command.create({
                'product_id': component02.id,
                'product_qty': 1,
                'cost_share': 0,
            }), Command.create({
                'product_id': component03.id,
                'product_qty': 1,
                'cost_share': 0,
            }), Command.create({
                'product_id': component04.id,
                'product_qty': 1,
                'cost_share': 0,
            })],
        })

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.vendor01.id,
            'order_line': [
                Command.create({
                    'product_id': kit_a.id,
                    'product_qty': 1,
                    'price_unit': 1000,
                    'tax_ids': [Command.clear()],
                }),
            ],
        })
        purchase_order.button_confirm()
        receipt = purchase_order.picking_ids
        receipt.button_validate()

        self.assertRecordValues(component01.stock_valuation_layer_ids, [{'value': 500.0, 'unit_cost': 500.0, 'quantity': 1.0}])
        self.assertRecordValues(component02.stock_valuation_layer_ids, [{'value': 170.0, 'unit_cost': 170.0, 'quantity': 1.0}])
        self.assertRecordValues(component03.stock_valuation_layer_ids, [{'value': 170.0, 'unit_cost': 170.0, 'quantity': 1.0}])
        self.assertRecordValues(component04.stock_valuation_layer_ids, [{'value': 160.0, 'unit_cost': 160.0, 'quantity': 1.0}])

        self.assertEqual(sum(purchase_order.order_line.move_ids.mapped('cost_share')), 1.0)
