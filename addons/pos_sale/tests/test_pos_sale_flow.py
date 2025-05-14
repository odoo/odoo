# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests.common import Form
from odoo import fields, Command

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSale(TestPointOfSaleHttpCommon):
    def test_settle_order_with_kit(self):
        if not self.env["ir.module.module"].search([("name", "=", "mrp"), ("state", "=", "installed")]):
            self.skipTest("mrp module is required for this test")

        self.kit = self.env['product.product'].create({
            'name': 'Pizza Chicken',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
        })

        self.component_a = self.env['product.product'].create({
            'name': 'Chicken',
            'type': 'product',
            'available_in_pos': True,
            'uom_id': self.env.ref('uom.product_uom_gram').id,
            'uom_po_id': self.env.ref('uom.product_uom_gram').id,
            'lst_price': 10.0,
        })
        self.location = self.env['stock.location'].create({
            'name': 'Test location',
            'usage': 'internal',
        })

        self.env['stock.quant']._update_available_quantity(self.component_a, self.location, 100000)

        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_id = self.kit
        bom_product_form.product_tmpl_id = self.kit.product_tmpl_id
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 300.0
        self.bom_a = bom_product_form.save()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.kit.id,
                'name': self.kit.name,
                'product_uom_qty': 10,
                'product_uom': self.kit.uom_id.id,
                'price_unit': self.kit.lst_price,
            })],
        })
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.quantity = 300
        picking.move_ids.picked = True
        action = picking.button_validate()
        wizard = Form(self.env[action['res_model']].with_context(action['context']))
        wizard.save().process()

        self.assertEqual(sale_order.order_line.qty_delivered, 1)

        self.pos_user.write({
            'groups_id': [
                (4, self.env.ref('stock.group_stock_user').id),
                (4, self.env.ref('sales_team.group_sale_salesman_all_leads').id),
            ]
        })
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrder', login="pos_user")

        #assert that sales order qty are correctly updated
        self.assertEqual(sale_order.order_line.qty_delivered, 3)
        self.assertEqual(sale_order.picking_ids[0].move_ids.product_qty, 2100) # 7 left to deliver => 300 * 7 = 2100
        self.assertEqual(sale_order.picking_ids[0].move_ids.quantity, 0)
        self.assertEqual(sale_order.picking_ids[1].move_ids.product_qty, 300)
        self.assertEqual(sale_order.picking_ids[1].move_ids.quantity, 300) # 1 delivered => 300 * 2 = 600

    def test_settle_order_with_incompatible_partner(self):
        """ If the partner of the sale order is not compatible with the current pos order,
            then a new pos order should be to settle the newly selected sale order.
        """

        product1 = self.env['product.product'].create({
            'name': 'product1',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10,
            'taxes_id': [odoo.Command.clear()],
        })
        product2 = self.env['product.product'].create({
            'name': 'product2',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 11,
            'taxes_id': [odoo.Command.clear()],
        })
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner 1'})
        partner_2 = self.env['res.partner'].create({'name': 'Test Partner 2'})
        self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'partner_shipping_id': partner_2.id,
            'order_line': [(0, 0, {'product_id': product1.id})],
        })
        self.env['sale.order'].create({
            'partner_id': partner_1.id,
            'partner_shipping_id': partner_1.id,
            'order_line': [(0, 0, {'product_id': product2.id})],
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderIncompatiblePartner', login="accountman")

    def test_settle_order_with_different_product(self):
        """This test create an order and settle it in the PoS. But only one of the product is delivered.
            And we need to make sure the quantity are correctly updated on the sale order.
        """
        #create 2 products
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
        })
        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
        })
        #create a sale order with 2 lines
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'product_uom': product_b.uom_id.id,
                'price_unit': product_b.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)
        self.assertEqual(sale_order.order_line[1].qty_delivered, 0)

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrder2', login="accountman")

        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.order_line[1].qty_delivered, 0)
        orderline_product_a = sale_order.order_line.filtered(lambda l: l.product_id.id == product_a.id)
        orderline_product_b = sale_order.order_line.filtered(lambda l: l.product_id.id == product_b.id)
        # nothing to deliver for product a because already handled in pos.
        self.assertEqual(orderline_product_a.move_ids.product_uom_qty, 0)
        # 1 item to deliver for product b.
        self.assertEqual(orderline_product_b.move_ids.product_uom_qty, 1)

    def test_downpayment_refund(self):
        #create a sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'product_uom': self.product_a.uom_id.id
            })],
        })
        sale_order.action_confirm()
        #set downpayment product in pos config
        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosRefundDownpayment', login="accountman")
        self.assertEqual(len(sale_order.order_line), 3)
        self.assertEqual(sale_order.order_line[1].qty_invoiced, 1)
        self.assertEqual(sale_order.order_line[2].qty_invoiced, -1)

    def test_settle_order_unreserve_order_lines(self):
        #create a product category that use the closest location for the removal strategy
        self.removal_strategy = self.env['product.removal'].search([('method', '=', 'closest')], limit=1)
        self.product_category = self.env['product.category'].create({
            'name': 'Product Category',
            'removal_strategy_id': self.removal_strategy.id,
        })

        self.product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'taxes_id': False,
            'categ_id': self.product_category.id,
        })

        #create 2 stock location Shelf 1 and Shelf 2
        self.warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.shelf_1 = self.env['stock.location'].create({
            'name': 'Shelf 1',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })
        self.shelf_2 = self.env['stock.location'].create({
            'name': 'Shelf 2',
            'usage': 'internal',
            'location_id': self.warehouse.lot_stock_id.id,
        })

        quants = self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 2,
            'location_id': self.shelf_1.id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product.id,
            'inventory_quantity': 5,
            'location_id': self.shelf_2.id,
        })
        quants.action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'name': self.product.name,
                'product_uom_qty': 4,
                'price_unit': self.product.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[0].quantity, 2)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[0].location_id.id, self.shelf_1.id)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[1].quantity, 2)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[1].location_id.id, self.shelf_2.id)

        self.main_pos_config.company_id.write({'point_of_sale_update_stock_quantities': 'real'})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderRealTime', login="accountman")
        self.main_pos_config.current_session_id.close_session_from_ui()
        pos_order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(pos_order.picking_ids.move_line_ids[0].quantity, 2)
        self.assertEqual(pos_order.picking_ids.move_line_ids[0].location_id.id, self.shelf_1.id)
        self.assertEqual(pos_order.picking_ids.move_line_ids[1].quantity, 2)
        self.assertEqual(pos_order.picking_ids.move_line_ids[1].location_id.id, self.shelf_2.id)
        self.assertEqual(sale_order.order_line.move_ids.move_lines_count, 0)

    def test_settle_order_with_multistep_delivery(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """

        #get the warehouse
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
        })
        self.env['stock.quant']._update_available_quantity(product_a, warehouse.lot_stock_id, 1)

        #create a sale order with 2 lines
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrder3', login="accountman")

        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.picking_ids.mapped('state'), ['cancel', 'cancel', 'cancel'])

    def test_pos_not_groupable_product(self):
        #Create a UoM Category that is not pos_groupable
        uom_category = self.env['uom.category'].create({
            'name': 'Test',
            'is_pos_groupable': False,
        })
        uom = self.env['uom.uom'].create({
            'name': 'Test',
            'category_id': uom_category.id,
            'uom_type': 'reference',
            'rounding': 0.01
        })
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'uom_id': uom.id,
            'uom_po_id': uom.id,
        })
        #create a sale order with product_a
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 3.5,
                'product_uom': product_a.uom_id.id,
                'price_unit': 8,  # manually set a different price than the lst_price
                'discount': 10,
            })],
        })
        self.assertEqual(sale_order.amount_total, 28.98)  # 3.5 * 8 * 1.15 * 90%
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderNotGroupable', login="accountman")

    def test_customer_notes(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """

        #create a sale order with 2 customer notes
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'note': 'Customer note 1',
            'order_line': [(0, 0, {
                'product_id': self.whiteboard_pen.id,
                'name': self.whiteboard_pen.name,
                'product_uom_qty': 1,
                'product_uom': self.whiteboard_pen.uom_id.id,
                'price_unit': self.whiteboard_pen.lst_price,
            }), (0, 0, {
                'name': 'Customer note 2',
                'display_type': 'line_note',
            }), (0, 0, {
                'name': 'Customer note 3',
                'display_type': 'line_note',
            })],
        })

        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderWithNote', login="accountman")

    def test_pos_invoice_analytic_account(self):
        #create a sale order with product_a
        self.analytic_plan_projects = self.env['account.analytic.plan'].create({'name': 'Projects'})
        self.analytic_plan_departments = self.env['account.analytic.plan'].create({'name': 'Departments test'})

        self.analytic_account_partner_a_1 = self.env['account.analytic.account'].create({
            'name': 'analytic_account_partner_a_1',
            'partner_id': self.partner_a.id,
            'plan_id': self.analytic_plan_projects.id,
        })
        self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.desk_pad.id,
                'name': self.desk_pad.name,
                'product_uom_qty': 3.5,
                'product_uom': self.desk_pad.uom_id.id,
                'price_unit': self.desk_pad.lst_price,
            })],
            'analytic_account_id': self.analytic_account_partner_a_1.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleAndInvoiceOrder', login="accountman")

        pos_order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertTrue(pos_order.account_move.line_ids[0].analytic_distribution, "Analytic distribution should be set on the invoice line")
        self.assertEqual(pos_order.account_move.line_ids[0].analytic_distribution.get(str(self.analytic_account_partner_a_1.id)), 100)

    def test_order_sales_count(self):
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id
        partner_1 = self.env['res.partner'].create({'name': 'Test Partner'})
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': partner_1.id,
            'pricelist_id': partner_1.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.desk_pad.id,
                'price_unit': self.desk_pad.lst_price,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': [],
                'price_subtotal': self.desk_pad.lst_price,
                'price_subtotal_incl': self.desk_pad.lst_price,
            })],
            'amount_total': self.desk_pad.lst_price,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}'
        })
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': current_session.payment_method_ids[0].id,
        })
        order_payment.with_context(**payment_context).check()

        current_session.close_session_from_ui()
        self.env.flush_all()
        self.assertEqual(self.desk_pad.sales_count, 1)

    def test_quotation_saving(self):
        """ Verify that a saved quotation doesn't change the state of the quotation """
        trusted_pos_config = self.env['pos.config'].create({
            'name': 'Trusted Shop',
            'module_pos_restaurant': False,
        })

        product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'taxes_id': False,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 4,
                'price_unit': product.lst_price,
            })],
        })
        self.assertEqual(sale_order.state, 'draft')

        self.main_pos_config.trusted_config_ids = trusted_pos_config.ids
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosQuotationSaving', login="accountman")

        self.assertEqual(sale_order.state, 'draft')

    def test_untaxed_invoiced_amount(self):
        """Make sure that orders invoiced in the pos gets their untaxed invoiced
           amount updated accordingly"""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'taxes_id': [],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 5.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'product_uom': product_b.uom_id.id,
                'price_unit': product_b.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        pos_order = {'data':
          {'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': partner_test.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': 10,
              'product_id': product_a.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0],
              'sale_order_origin_id': sale_order,
              'qty': 1,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'pos_session_id': current_session.id,
           'sequence_number': self.main_pos_config.journal_id.id,
           'statement_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'uid': '00044-003-0014',
           'user_id': self.env.uid},
            }

        self.env['pos.order'].create_from_ui([pos_order])
        self.assertEqual(sale_order.order_line[0].untaxed_amount_invoiced, 10, "Untaxed invoiced amount should be 10")
        self.assertEqual(sale_order.order_line[1].untaxed_amount_invoiced, 0, "Untaxed invoiced amount should be 0")

    def test_order_does_not_remain_in_list(self):
        """Verify that a paid order doesn't remain in the orders list"""

        # Create a sale order
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.whiteboard_pen.id,
                'name': self.whiteboard_pen.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'product_uom': self.whiteboard_pen.uom_id.id
            })],
        })

        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosOrderDoesNotRemainInList', login="accountman")

    def test_settle_order_change_customer(self):
        """
        When settling an order, the price set on the sol shouldn't reset to
        the sale price of the product when changing customer.
        """
        self.product_a.lst_price = 150
        self.product_a.taxes_id = None
        self.product_a.available_in_pos = True
        self.env['res.partner'].create({'name': 'Test Partner AAA'})
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        sale_order.action_confirm()

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleCustomPrice', login="accountman")

    def test_downpayment_with_taxed_product(self):
        tax_1 = self.env['account.tax'].create({
            'name': '10',
            'amount': 10,
        })

        tax_2 = self.env['account.tax'].create({
            'name': '5 incl',
            'amount': 5,
            'price_include': True,
        })

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'taxes_id': [tax_1.id],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 5.0,
            'taxes_id': [tax_2.id],
        })

        product_c = self.env['product.product'].create({
            'name': 'Product C',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 15.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'product_uom': product_b.uom_id.id,
                'price_unit': product_b.lst_price,
            }), (0, 0, {
                'product_id': product_c.id,
                'name': product_c.name,
                'product_uom_qty': 1,
                'product_uom': product_c.uom_id.id,
                'price_unit': product_c.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PoSDownPaymentLinesPerTax', login="accountman")

        # We check the content of the invoice to make sure Product A/B/C only appears only once
        invoice_pdf_content = str(self.env['pos.order'].search([]).account_move.get_invoice_pdf_report_attachment()[0])
        self.assertEqual(invoice_pdf_content.count('Product A'), 1)
        self.assertEqual(invoice_pdf_content.count('Product B'), 1)
        self.assertEqual(invoice_pdf_content.count('Product C'), 1)

    def test_settle_draft_order_service_product(self):
        """
        Checks that, when settling a draft order (quotation), the quantity set on the corresponding
        PoS order, for service products, is set correctly.
        """

        product_a = self.env['product.product'].create({
            'name': 'Test service product',
            'available_in_pos': True,
            'type': 'service',
            'invoice_policy': 'order',
            'lst_price': 50.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })

        self.assertEqual(sale_order.state, 'draft')

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleDraftOrder', login="accountman")

    def test_ship_later_no_default(self):
        """ Verify that when settling an order the ship later is not activated by default"""
        product = self.env['product.product'].create({
            'name': 'Product',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'taxes_id': False,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': 4,
                'price_unit': product.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.write({'ship_later': True})
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosShipLaterNoDefault', login="accountman")

    def test_downpayment_amount_to_invoice(self):
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 100.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PoSDownPaymentAmount', login="accountman")
        self.assertEqual(sale_order.amount_to_invoice, 80.0, "Downpayment amount not considered!")

        self.assertEqual(sale_order.order_line[1].price_unit, 20)

        # Update delivered quantity of SO line
        sale_order.order_line[0].write({'qty_delivered': 1.0})
        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        # Let's do the invoice for the remaining amount
        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'deposit_account_id': self.company_data['default_account_revenue'].id
        })
        payment.create_invoices()

        # Confirm all invoices
        sale_order.invoice_ids.action_post()
        self.assertEqual(sale_order.order_line[1].price_unit, 20)

    def test_settle_order_with_multistep_delivery_receipt(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """
        if not self.env["ir.module.module"].search([("name", "=", "purchase"), ("state", "=", "installed")]):
            self.skipTest("purchase module is required for this test")

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        warehouse.reception_steps = 'three_steps'
        self.env.ref('stock.route_warehouse0_mto').active = True
        route_buy = self.env.ref('purchase_stock.route_warehouse0_buy')
        route_mto = self.env.ref('stock.route_warehouse0_mto')
        self.partner_test = self.env['res.partner'].create({
            'name': 'Partner Test A',
            'is_company': True,
            'street': '77 Santa Barbara Rd',
            'city': 'Pleasant Hill',
            'country_id': self.env.ref('base.nl').id,
            'zip': '1105AA',
            'state_id': False,
            'email': 'deco.addict82@example.com',
            'phone': '(603)-996-3829',
        })

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'seller_ids': [(0, 0, {
                'partner_id': self.partner_test.id,
                'min_qty': 1.0,
                'price': 1.0,
            })],
            'route_ids': [(6, 0, [route_buy.id, route_mto.id])],
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        # We validate the purchase and receipt steps
        po = sale_order._get_purchase_orders()
        po.button_confirm()
        picking = po.picking_ids[0]
        picking.button_validate()
        sale_order.picking_ids.filtered(lambda p: p.state == 'assigned').button_validate()
        sale_order.picking_ids.filtered(lambda p: p.state == 'assigned').button_validate()

        self.main_pos_config.ship_later = True
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrder4', login="accountman")

        self.assertEqual(sale_order.picking_ids.mapped('state'), ['cancel', 'cancel', 'cancel', 'done', 'done'])
        self.assertEqual(sale_order.pos_order_line_ids.order_id.picking_ids.mapped('state'), ['waiting', 'waiting', 'assigned'])

    def test_settle_order_ship_later_delivered_qty(self):
        """This test create an order, settle it in the PoS and ship it later.
            We need to make sure that the quantity delivered on the original sale is updated correctly
        """

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
        })

        partner_test = self.env['res.partner'].create({
            'name': 'Test Partner',
            'city': 'San Francisco',
            'state_id': self.env.ref('base.state_us_5').id,
            'country_id': self.env.ref('base.us').id,
            'zip': '94134',
            'street': 'Rue du burger',
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)

        self.main_pos_config.ship_later = True
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderShipLater', login="accountman")

        # The pos order is being shipped later so the qty_delivered should still be 0
        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)

        # We validate the delivery of the order, now the qty_delivered should be 1
        pickings = sale_order.pos_order_line_ids.order_id.picking_ids
        pickings.move_ids.quantity = 1
        pickings.button_validate()
        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)

    def test_downpayment_invoice(self):
        """This test check that users that don't have the pos user group can invoice downpayments"""
        self.env['res.partner'].create({'name': 'Test Partner AAA'})

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner BBB'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_a.id,
                'name': self.product_a.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_id': False,
            })],
        })
        sale_order.action_confirm()

        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        payment = self.env['sale.advance.payment.inv'].with_context(context).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 100,
            'deposit_account_id': self.company_data['default_account_revenue'].id,
        })
        payment.create_invoices()
        all_groups = self.user.groups_id
        self.user.groups_id = self.env.ref('account.group_account_manager') + self.env.ref('sales_team.group_sale_salesman_all_leads')

        downpayment_line = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        downpayment_invoice = downpayment_line.order_id.order_line.invoice_lines.move_id
        downpayment_invoice.action_post()
        self.user.groups_id = all_groups
        self.assertEqual(downpayment_line.price_unit, 100)

    def test_downpayment_with_fixed_taxed_product(self):
        """This test will make sure that a unique downpayment line will be created for the fixed tax"""
        tax_1 = self.env['account.tax'].create({
            'name': '10',
            'amount': 10,
            'amount_type': 'fixed',
        })

        tax_2 = self.env['account.tax'].create({
            'name': '5 incl',
            'amount': 5,
            'price_include': True,
        })

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 100.0,
            'taxes_id': [tax_1.id],
        })

        product_b = self.env['product.product'].create({
            'name': 'Product B',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 5.0,
            'taxes_id': [tax_2.id],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            }), (0, 0, {
                'product_id': product_b.id,
                'name': product_b.name,
                'product_uom_qty': 1,
                'product_uom': product_b.uom_id.id,
                'price_unit': product_b.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PoSDownPaymentFixedTax', login="accountman")

    def test_downpayment_line_name(self):
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 100.0,
            'taxes_id': [],
        })
        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()

        downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.main_pos_config.write({
            'down_payment_product_id': downpayment_product.id,
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PoSDownPaymentAmount', login="accountman")

        downpayment_line_pos = sale_order.order_line.filtered('is_downpayment')
        self.assertTrue(downpayment_line_pos)
        self.assertNotIn('(draft)', downpayment_line_pos.name.lower())
        self.assertNotIn('(canceled)', downpayment_line_pos.name.lower())

    def test_pos_order_and_invoice_amounts(self):
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
        partner_test = self.env['res.partner'].create({
            'name': 'Test Partner',
            'property_payment_term_id': payment_term.id,
        })

        tax = self.env['account.tax'].create({
            'name': 'Tax 10%',
            'amount': 10,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
        })
        test_product = self.env['product.product'].create({
            'name': 'Product Test',
            'available_in_pos': True,
            'list_price': 1000,
            'taxes_id': [(6, 0, [tax.id])],
        })

        self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': test_product.id,
                'name': test_product.name,
                'price_unit': test_product.lst_price,
            })],
        })

        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleAndInvoiceOrder', login="accountman")

        order = self.env['pos.order'].search([('partner_id', '=', partner_test.id)], limit=1)
        self.assertTrue(order)
        self.assertEqual(order.partner_id, partner_test)

        invoice = self.env['account.move'].search([('invoice_origin', '=', order.name)], limit=1)
        self.assertTrue(invoice)
        self.assertFalse(invoice.invoice_payment_term_id) 

        self.assertAlmostEqual(order.amount_total, invoice.amount_total, places=2, msg="Order and Invoice amounts do not match.")

    def test_amount_to_invoice(self):
        """
        Checks that the amount to invoice is updated correctly when paying an order in the PoS
        """

        product_a = self.env['product.product'].create({
            'name': 'Test service product',
            'available_in_pos': True,
            'type': 'service',
            'invoice_policy': 'order',
            'lst_price': 100.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        self.main_pos_config.open_ui()
        order_data = {
            "amount_paid": 100,
            "amount_tax": 0,
            "amount_return": 0,
            "amount_total": 100,
            "pos_session_id": self.main_pos_config.current_session_id.id,
            "date_order": fields.Datetime.to_string(fields.Datetime.now()),
            "fiscal_position_id": False,
            "lines": [
                Command.create({
                    "discount": 0,
                    "pack_lot_ids": [],
                    "price_unit": 100.0,
                    "product_id": self.product_a.id,
                    "price_subtotal": 100.0,
                    "price_subtotal_incl": 100.0,
                    "tax_ids": [],
                    "sale_order_line_id": sale_order.order_line[0],
                    "sale_order_origin_id": sale_order,
                    "qty": 1,
                }),
            ],
            "name": "Order 12345-123-1234",
            "partner_id": self.partner_a.id,
            "session_id": self.main_pos_config.current_session_id.id,
            "sequence_number": 2,
            "statement_ids": [
                    Command.create({
                        "amount": 100,
                        "name": fields.Datetime.now(),
                        "payment_method_id": self.main_pos_config.payment_method_ids[0].id,
                    }),
            ],
            "uuid": "12345-123-1234",
            "last_order_preparation_change": "{}",
            "user_id": self.env.uid,
            "to_invoice": True,
        }
        self.assertEqual(sale_order.amount_to_invoice, 100.0, "Amount to invoice should be 100.0")
        self.env['pos.order'].create_from_ui([{"data": order_data}])
        self.assertEqual(sale_order.amount_to_invoice, 0.0, "Amount to invoice should be 0.0")

    def test_payment_terms_with_early_discount(self):
        """Make sure that orders invoiced in the pos do not use payment terms with early discount"""

        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'available_in_pos': True,
            'type': 'product',
            'lst_price': 10.0,
            'taxes_id': [],
        })

        partner_test = self.env['res.partner'].create({'name': 'Test Partner'})

        payment_terms = self.env['account.payment.term'].create({
            'name': "Test Payment Term",
            'early_discount': True,
            'line_ids': [(0, 0, {
                'value': 'percent',
                'value_amount': 100,
                'nb_days': 45,
            })]
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': partner_test.id,
            'payment_term_id': payment_terms.id,
            'order_line': [(0, 0, {
                'product_id': product_a.id,
                'name': product_a.name,
                'product_uom_qty': 1,
                'product_uom': product_a.uom_id.id,
                'price_unit': product_a.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        current_session = self.main_pos_config.current_session_id

        pos_order = {'data':
          {'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': partner_test.id,
           'pricelist_id': self.main_pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': 10,
              'product_id': product_a.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0],
              'sale_order_origin_id': sale_order,
              'qty': 1,
              'tax_ids': []}]],
           'name': 'Order 00044-003-0014',
           'pos_session_id': current_session.id,
           'sequence_number': self.main_pos_config.journal_id.id,
           'statement_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.main_pos_config.payment_method_ids[0].id}]],
           'uid': '00044-003-0014',
           'user_id': self.env.uid},
            }

        pos_order_id = self.env['pos.order'].create_from_ui([pos_order])[0]['id']
        pos_order = self.env['pos.order'].browse(pos_order_id)
        self.assertFalse(pos_order.account_move.invoice_payment_term_id)
