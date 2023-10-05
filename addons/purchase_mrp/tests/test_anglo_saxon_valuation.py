# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Date
from odoo.tools import mute_logger
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase
from odoo.addons.stock_account.tests.test_stockvaluation import _create_accounting_data


@tagged('post_install', '-at_install')
class TestAngloSaxonValuationPurchaseMRP(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestAngloSaxonValuationPurchaseMRP, cls).setUpClass()
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
            'type': 'product',
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
        stock_location = self.env.ref('stock.stock_location_stock')
        customer_location = self.env.ref('stock.stock_location_customers')
        type_out = self.env.ref('stock.picking_type_out')
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_litre = self.env.ref('uom.product_uom_litre')

        component01, component02 = self.env['product.product'].create([{
            'name': 'Component %s' % name,
            'type': 'product',
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
        action = wizard.create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        return_picking.move_ids.move_line_ids.quantity = 1
        return_picking.button_validate()

        self.assertEqual(component01.stock_valuation_layer_ids.mapped('value'), [25, -25, 25])
        self.assertEqual(component02.stock_valuation_layer_ids.mapped('value'), [75, -75, 75])
