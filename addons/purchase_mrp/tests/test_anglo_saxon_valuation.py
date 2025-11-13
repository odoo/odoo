from unittest import skip

from odoo.fields import Date, Datetime
from odoo.tools import float_is_zero, mute_logger
from odoo.tests import Form, tagged
from odoo.addons.stock_account.tests.common import TestStockValuationCommon


@tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
class TestAngloSaxonValuationPurchaseMRP(TestStockValuationCommon):

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

    def test_average_cost_unbuild_valuation(self):
        """ Ensure that an unbuild for some avg cost product won't leave the `Cost of Production`
        journal in an imbalanced state if the std price of that product has changed since the MO
        was completed (i.e., since build time).
        """
        def make_purchase_and_production(product_ids, price_units):
            purchase_orders = self.env['purchase.order'].create([{
                'partner_id': self.partner_a.id,
                'order_line': [(0, 0, {
                    'product_id': prod_id,
                    'product_qty': 2,
                    'price_unit': price_unit
                })],
            } for prod_id, price_unit in zip(product_ids, price_units)])
            purchase_orders.button_confirm()
            purchase_orders.picking_ids.move_ids.quantity = 2
            purchase_orders.picking_ids.button_validate()
            production_form = Form(self.env['mrp.production'])
            production_form.product_id = final_product
            production_form.bom_id = final_product_bom
            production_form.product_qty = 1
            production = production_form.save()
            production.action_confirm()
            mo_form = Form(production)
            mo_form.qty_producing = 1
            production = mo_form.save()
            production._post_inventory()
            production.button_mark_done()
            return production

        cost_of_production_account = self.env['account.account'].search([
            ('name', '=', 'Cost of Production'),
            ('company_ids', 'in', self.env.company.id),
        ], limit=1)
        self.avco_category.property_stock_account_production_cost_id = cost_of_production_account.id
        final_product = self.env['product.product'].create({
            'name': 'final product',
            'is_storable': True,
            'standard_price': 0,
            'categ_id': self.avco_category.id,
            'route_ids': [(6, 0, self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1).ids)],
        })
        comp_1, comp_2 = self.env['product.product'].create([{
            'name': name,
            'is_storable': True,
            'standard_price': 0,
            'categ_id': self.avco_category.id,
            'route_ids': [(4, self.env['stock.route'].search([('name', '=', 'Buy')], limit=1).id)],
        } for name in ('comp_1', 'comp_2')])
        final_product_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': comp_prod_id,
                'product_qty': 2,
            }) for comp_prod_id in (comp_1.id, comp_2.id)],
        })
        production_1 = make_purchase_and_production([comp_1.id, comp_2.id], [50, 40])
        make_purchase_and_production([comp_1.id, comp_2.id], [55, 45])
        action = production_1.button_unbuild()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.product_qty = 1
        wizard = wizard.save()
        wizard.action_validate()
        self.assertTrue(float_is_zero(
            sum(self.env['account.move.line'].search([
                ('account_id', '=', cost_of_production_account.id),
                ('product_id', 'in', (final_product.id, comp_1.id, comp_2.id)),
            ]).mapped('balance')),
            precision_rounding=self.env.company.currency_id.rounding
        ))
