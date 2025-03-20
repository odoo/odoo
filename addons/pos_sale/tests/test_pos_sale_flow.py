# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo.tests import Form
from odoo import fields, Command
from odoo.tools import format_date

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSale(TestPointOfSaleDataHttpCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_manager')
        self.env.user.group_ids += self.env.ref('stock.group_stock_manager')
        self.product_awesome_article.write({
            'list_price': 10.0,
            'is_storable': True,
        })
        self.product_awesome_item.write({
            'list_price': 10.0,
            'is_storable': True,
        })
        self.product_awesome_thing.write({
            'list_price': 10.0,
            'is_storable': True,
        })
        self.item_product_variant = self.product_awesome_item.product_variant_ids[0]
        self.thing_product_variant = self.product_awesome_thing.product_variant_ids[0]
        self.article_product_variant = self.product_awesome_article.product_variant_ids[0]

    def test_settle_order_with_kit(self):
        if not self.env["ir.module.module"].search([("name", "=", "mrp"), ("state", "=", "installed")]):
            self.skipTest("mrp module is required for this test")

        self.env.user.write({
            'group_ids': [(4, self.env.ref('stock.group_stock_manager').id), (4, self.env.ref('mrp.group_mrp_manager').id)],
        })
        self.product_awesome_item.write({
            'is_storable': True,
        })
        self.product_awesome_article.write({
            'is_storable': True,
        })
        self.location = self.env['stock.location'].create({
            'name': 'Test location',
            'usage': 'internal',
        })
        self.env['stock.quant']._update_available_quantity(self.product_awesome_article.product_variant_id, self.location, 100000)
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_tmpl_id = self.product_awesome_item
        bom_product_form.product_qty = 1.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.product_awesome_article.product_variant_id
            bom_line.product_qty = 300.0
        self.bom_a = bom_product_form.save()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.product_awesome_item.product_variant_id.id,
                'name': self.product_awesome_item.name,
                'product_uom_qty': 10,
                'price_unit': self.product_awesome_item.product_variant_id.lst_price,
            })],
        })
        sale_order.action_confirm()
        picking = sale_order.picking_ids
        picking.move_ids.quantity = 300
        picking.move_ids.picked = True
        Form.from_action(self.env, picking.button_validate()).save().process()

        self.assertEqual(sale_order.order_line.qty_delivered, 1)

        self.pos_user.write({
            'group_ids': [
                (4, self.env.ref('stock.group_stock_user').id),
                (4, self.env.ref('sales_team.group_sale_salesman_all_leads').id),
                (4, self.env.ref('account.group_account_user').id),
                (4, self.env.ref('base.group_system').id), # FIXME refacto
            ]
        })
        self.start_pos_tour('PosSettleOrder')
        self.assertEqual(sale_order.order_line.qty_delivered, 3)
        self.assertEqual(sale_order.picking_ids[0].move_ids.product_qty, 2100) # 7 left to deliver => 300 * 7 = 2100
        self.assertEqual(sale_order.picking_ids[0].move_ids.quantity, 0)
        self.assertEqual(sale_order.picking_ids[1].move_ids.product_qty, 300)
        self.assertEqual(sale_order.picking_ids[1].move_ids.quantity, 300) # 1 delivered => 300 * 2 = 600

    def test_settle_order_with_incompatible_partner(self):
        self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'partner_shipping_id': self.partner_two.id,
            'order_line': [(0, 0, {'product_id': self.product_awesome_item.product_variant_ids[0].id})],
        })
        self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'partner_shipping_id': self.partner_one.id,
            'order_line': [(0, 0, {'product_id': self.product_awesome_article.product_variant_ids[0].id})],
        })
        self.start_pos_tour('PosSettleOrderIncompatiblePartner', login="accountman")

    def test_settle_order_with_different_product(self):
        """This test create an order and settle it in the PoS. But only one of the product is delivered.
            And we need to make sure the quantity are correctly updated on the sale order.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.product_awesome_item.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            }), (0, 0, {
                'product_id': self.article_product_variant.id,
                'name': self.product_awesome_article.name,
                'product_uom_qty': 1,
                'price_unit': self.article_product_variant.lst_price,
            }), (0, 0, {
                # Add this line to test that it should not cause any issue when settling this order.
                'name': 'section line',
                'display_type': 'line_section',
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)
        self.assertEqual(sale_order.order_line[1].qty_delivered, 0)

        self.start_pos_tour('PosSettleOrder2', login="accountman")
        sale_order = self.env['sale.order'].browse(sale_order.id)
        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.order_line[1].qty_delivered, 0)
        orderline_product_a = sale_order.order_line.filtered(lambda l: l.product_id.id == self.item_product_variant.id)
        orderline_product_b = sale_order.order_line.filtered(lambda l: l.product_id.id == self.article_product_variant.id)
        # nothing to deliver for product a because already handled in pos.
        self.assertEqual(orderline_product_a.move_ids.product_uom_qty, 0)
        # 1 item to deliver for product b.
        self.assertEqual(orderline_product_b.move_ids.product_uom_qty, 1)

    def test_downpayment_refund(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        sale_order.action_confirm()
        #set downpayment product in pos config
        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
        })
        self.pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.start_pos_tour('PosRefundDownpayment', login="accountman")
        self.assertEqual(len(sale_order.order_line), 4)
        self.assertEqual(sale_order.order_line[2].qty_invoiced, 1)
        self.assertEqual(sale_order.order_line[3].qty_invoiced, -1)

    def test_settle_order_unreserve_order_lines(self):
        #create a product category that use the closest location for the removal strategy
        self.removal_strategy = self.env['product.removal'].search([('method', '=', 'closest')], limit=1)
        self.product_category = self.env['product.category'].create({
            'name': 'Product Category',
            'removal_strategy_id': self.removal_strategy.id,
        })
        self.product_awesome_item.write({
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
            'product_id': self.item_product_variant.id,
            'inventory_quantity': 2,
            'location_id': self.shelf_1.id,
        })
        quants |= self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.item_product_variant.id,
            'inventory_quantity': 5,
            'location_id': self.shelf_2.id,
        })
        quants.action_apply_inventory()

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 4,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[0].quantity, 2)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[0].location_id.id, self.shelf_1.id)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[1].quantity, 2)
        self.assertEqual(sale_order.order_line.move_ids.move_line_ids[1].location_id.id, self.shelf_2.id)

        self.pos_config.company_id.write({'point_of_sale_update_stock_quantities': 'real'})
        self.start_pos_tour('PosSettleOrderRealTime', login="accountman")
        self.pos_config.current_session_id.close_session_from_ui()
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
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        warehouse.delivery_steps = 'pick_pack_ship'
        self.env['stock.quant']._update_available_quantity(self.item_product_variant, warehouse.lot_stock_id, 1)

        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()

        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)
        self.start_pos_tour('PosSettleOrder3', login="accountman")
        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)
        self.assertEqual(sale_order.picking_ids.mapped('state'), ['cancel'])

    def test_pos_not_groupable_product(self):
        #Create a UoM Category that is not pos_groupable
        uom = self.env['uom.uom'].create({
            'name': 'Test',
        })
        self.product_awesome_item.write({
            'uom_id': uom.id,
            'taxes_id': False,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 3.5,
                'price_unit': 8,  # manually set a different price than the lst_price
                'discount': 10,
            })],
        })
        self.assertEqual(sale_order.amount_total, 25.2)  # 3.5 * 8 - 10%
        self.start_pos_tour('PosSettleOrderNotGroupable', login="accountman")

    def test_customer_notes(self):
        """This test create an order and settle it in the PoS. It also uses multistep delivery
            and we need to make sure that all the picking are cancelled if the order is fully delivered.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'note': 'Customer note 1',
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            }), (0, 0, {
                'name': 'Customer note 2',
                'display_type': 'line_note',
            }), (0, 0, {
                'name': 'Customer note 3',
                'display_type': 'line_note',
            })],
        })
        sale_order.action_confirm()
        self.start_pos_tour('PosSettleOrderWithNote', login="accountman")

    def test_order_sales_count(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_one.id,
            'pricelist_id': self.partner_one.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.item_product_variant.id,
                'price_unit': self.item_product_variant.lst_price,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': [],
                'price_subtotal': self.item_product_variant.lst_price,
                'price_subtotal_incl': self.item_product_variant.lst_price,
            })],
            'amount_total': self.item_product_variant.lst_price,
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
        self.assertEqual(self.item_product_variant.sales_count, 1)

    def test_untaxed_invoiced_amount(self):
        """Make sure that orders invoiced in the pos gets their untaxed invoiced
           amount updated accordingly"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            }), (0, 0, {
                'product_id': self.article_product_variant.id,
                'name': self.article_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.article_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        pos_order = {
           'amount_paid': 10,
           'amount_return': 0,
           'amount_tax': 0,
           'amount_total': 10,
           'date_order': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'to_invoice': True,
           'partner_id': self.partner_one.id,
           'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'pack_lot_ids': [],
              'price_unit': 10,
              'product_id': self.item_product_variant.id,
              'price_subtotal': 10,
              'price_subtotal_incl': 10,
              'sale_order_line_id': sale_order.order_line[0].id,
              'sale_order_origin_id': sale_order.id,
              'qty': 1,
              'tax_ids': []}]],
           'session_id': current_session.id,
           'payment_ids': [[0,
             0,
             {'amount': 10,
              'name': fields.Datetime.now(),
              'payment_method_id': self.pos_config.payment_method_ids[0].id}]],
           'user_id': self.env.uid,
            }

        self.env['pos.order'].sync_from_ui([pos_order])
        self.assertEqual(sale_order.order_line[0].untaxed_amount_invoiced, 10, "Untaxed invoiced amount should be 10")
        self.assertEqual(sale_order.order_line[1].untaxed_amount_invoiced, 0, "Untaxed invoiced amount should be 0")

    def test_order_does_not_remain_in_list(self):
        """Verify that a paid order doesn't remain in the orders list"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })

        sale_order.action_confirm()
        self.start_pos_tour("PosOrderDoesNotRemainInList", login="accountman")

    def test_settle_draft_order_service_product(self):
        """
        Checks that, when settling a draft order (quotation), the quantity set on the corresponding
        PoS order, for service products, is set correctly.
        """
        self.item_product_variant.write({
            'type': 'service',
            'invoice_policy': 'order',
            'lst_price': 50.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })

        self.assertEqual(sale_order.state, 'draft')
        self.start_pos_tour('PosSettleDraftOrder', login="accountman", debug=True)

    def test_settle_order_change_customer(self):
        """
        When settling an order, the price set on the sol shouldn't reset to
        the sale price of the product when changing customer.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
        })
        sale_order.action_confirm()
        self.start_pos_tour('PosSettleCustomPrice', login="accountman")

    def test_so_with_downpayment(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.item_product_variant.name,
                    'product_id': self.item_product_variant.id,
                    'product_uom_qty': 10.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        down_payment = self.env['sale.advance.payment.inv'].create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 20,
            'sale_order_ids': so.ids,
        })
        down_payment.create_invoices()
        # Invoice the delivered part from the down payment
        down_payment_invoices = so.invoice_ids
        down_payment_invoices.action_post()
        self.pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.pos_config.down_payment_product_id.write({'active': True})
        self.start_pos_tour('PoSSaleOrderWithDownpayment', login="accountman")

    def test_downpayment_with_taxed_product(self):
        tax_1 = self.env['account.tax'].create({
            'name': '10',
            'amount': 10,
        })

        tax_2 = self.env['account.tax'].create({
            'name': '5 incl',
            'amount': 5,
            'price_include_override': 'tax_included',
        })
        self.item_product_variant.write({
            'taxes_id': [tax_1.id],
        })
        self.article_product_variant.write({
            'lst_price': 5.0,
            'taxes_id': [tax_2.id],
        })
        self.thing_product_variant.write({
            'lst_price': 15.0,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            }), (0, 0, {
                'product_id': self.article_product_variant.id,
                'name': self.article_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.article_product_variant.lst_price,
            }), (0, 0, {
                'product_id': self.thing_product_variant.id,
                'name': self.thing_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.thing_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.start_pos_tour('PoSDownPaymentLinesPerTax', login="accountman")

        # We check the content of the invoice to make sure Product A/B/C only appears only once
        invoice_pdf_content = str(self.env['pos.order'].search([]).account_move._get_invoice_legal_documents('pdf', allow_fallback=True).get('content'))
        self.assertEqual(invoice_pdf_content.count('Awesome Item'), 1)
        self.assertEqual(invoice_pdf_content.count('Awesome Article'), 1)
        self.assertEqual(invoice_pdf_content.count('Awesome Thing'), 1)

        for order_line in sale_order.order_line.filtered(lambda l: l.product_id == self.downpayment_product):
            order_line = order_line.with_context(lang=self.partner_one.lang)
            self.assertIn(format_date(order_line.env, order_line.order_id.date_order), order_line.name)

    def test_settle_so_with_pos_downpayment(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [
                (0, 0, {
                    'name': self.item_product_variant.name,
                    'product_id': self.item_product_variant.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Apply 10% down payment
        self.pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.start_pos_tour('PoSApplyDownpayment', login="accountman")
        invoice = so._create_invoices(final=True)
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 90)

    def test_ship_later_no_default(self):
        """ Verify that when settling an order the ship later is not activated by default"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 4,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.pos_config.write({'ship_later': True})
        self.start_pos_tour('PosShipLaterNoDefault', login="accountman")

    def test_order_sale_team(self):
        sale_team = self.env['crm.team'].create({'name': 'Test team'})
        self.pos_config.write({'crm_team_id': sale_team})
        self.pos_config.open_ui()
        self.start_pos_tour('PosSaleTeam', login="accountman")
        order = self.env['pos.order'].search([])
        self.assertEqual(len(order), 1)
        self.assertEqual(order.crm_team_id, sale_team)

    def test_show_orders_for_pos_currency_only(self):
        currency = self.env['res.currency'].create({
            'name': 'C',
            'symbol': 'C',
            'rounding': 0.01,
            'currency_unit_label': 'Curr',
            'rate': 1,
        })
        pricelist = self.env['product.pricelist'].create({
            'name': 'Pricelist Different Currency',
            'currency_id': currency.id,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 4,
                'price_unit': self.item_product_variant.lst_price,
            })],
            'pricelist_id': pricelist.id
        })
        sale_order.action_confirm()
        self.start_pos_tour('PosOrdersListDifferentCurrency', login="pos_admin")

    def test_downpayment_amount_to_invoice(self):
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.pos_config.down_payment_product_id = self.env.ref("pos_sale.default_downpayment_product")
        self.start_pos_tour('PoSDownPaymentAmount', login="accountman")
        self.assertEqual(sale_order.amount_to_invoice, 8.0, "Downpayment amount not considered!")
        self.assertEqual(sale_order.amount_invoiced, 2.0, "Downpayment amount not considered!")
        self.assertEqual(sale_order.order_line[2].price_unit, 2)

        # Update delivered quantity of SO line
        sale_order.order_line[0].write({'qty_delivered': 1.0})
        context = {
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }

        # Let's do the invoice for the remaining amount
        payment = self.env['sale.advance.payment.inv'].with_context(context).create({})
        payment.create_invoices()

        # Confirm all invoices
        sale_order.invoice_ids.action_post()
        self.assertEqual(sale_order.order_line[2].price_unit, 2)

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
        route_mto.rule_ids.procure_method = 'mts_else_mto'
        self.item_product_variant.write({
            'seller_ids': [(0, 0, {
                'partner_id': self.partner_one.id,
                'min_qty': 1.0,
                'price': 1.0,
            })],
            'route_ids': [(6, 0, [route_buy.id, route_mto.id])],
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()

        # We validate the purchase and receipt steps
        po = sale_order._get_purchase_orders()
        po.button_confirm()
        picking = po.picking_ids[0]
        picking.button_validate()
        self.env['stock.picking'].search([('group_id', '=', po.group_id.id)]).filtered(lambda p: p.state == 'assigned').button_validate()
        self.env['stock.picking'].search([('group_id', '=', po.group_id.id)]).filtered(lambda p: p.state == 'assigned').button_validate()

        self.pos_config.ship_later = True
        self.start_pos_tour('PosSettleOrder4', login="accountman")

        self.assertEqual(sale_order.picking_ids.state, 'cancel')
        self.assertEqual(sale_order.pos_order_line_ids.order_id.picking_ids.state, 'assigned')
        self.assertEqual(self.env['purchase.order.line'].search_count([('product_id', '=', self.item_product_variant.id)]), 1)

    def test_pos_sale_warnings(self):
        self.env['res.partner'].create([
            {'name': 'A Test Customer', 'sale_warn': 'warning', 'sale_warn_msg': 'Highly infectious disease'},
            {'name': 'A Test Customer 2', 'sale_warn': 'block', 'sale_warn_msg': 'Cannot afford our services'}
        ])
        self.start_pos_tour('PosSaleWarning', login="accountman")

    def test_downpayment_invoice(self):
        """This test check that users that don't have the pos user group can invoice downpayments"""
        self.env['res.partner'].create({'name': 'Test Partner AAA'})

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': 100,
                'tax_ids': False,
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
        })
        payment.create_invoices()
        selected_groups = self.user.group_ids
        self.user.group_ids = self.env.ref('account.group_account_manager') + self.env.ref('sales_team.group_sale_salesman_all_leads')

        downpayment_line = sale_order.order_line.filtered(lambda l: l.is_downpayment and not l.display_type)
        downpayment_invoice = downpayment_line.order_id.order_line.invoice_lines.move_id
        downpayment_invoice.action_post()
        self.user.group_ids = selected_groups
        self.assertEqual(downpayment_line.price_unit, 100)

    def test_settle_order_ship_later_delivered_qty(self):
        """This test create an order, settle it in the PoS and ship it later.
            We need to make sure that the quantity delivered on the original sale is updated correctly
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)
        self.pos_config.ship_later = True
        self.start_pos_tour('PosSettleOrderShipLater', login="pos_user")

        # The pos order is being shipped later so the qty_delivered should still be 0
        self.assertEqual(sale_order.order_line[0].qty_delivered, 0)

        # We validate the delivery of the order, now the qty_delivered should be 1
        pickings = sale_order.pos_order_line_ids.order_id.picking_ids
        pickings.move_ids.quantity = 1
        pickings.button_validate()
        self.assertEqual(sale_order.order_line[0].qty_delivered, 1)

    def test_draft_pos_order_linked_sale_order(self):
        """This test create an order and settle it in the PoS. It will let the PoS order in draft state.
           As the order is still in draft state it shouldn't have impact on invoiced qty of the linked sale order.
        """
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.start_pos_tour('PosSettleOrder5', login="accountman")
        self.assertEqual(sale_order.order_line.qty_invoiced, 0)
        self.assertEqual(sale_order.order_line.qty_delivered, 0)

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
            'price_include_override': 'tax_included',
        })
        self.item_product_variant.write({
            'lst_price': 100.0,
            'taxes_id': [tax_1.id],
        })
        self.article_product_variant.write({
            'lst_price': 5.0,
            'taxes_id': [tax_2.id],
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [(0, 0, {
                'product_id': self.item_product_variant.id,
                'name': self.item_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.item_product_variant.lst_price,
            }), (0, 0, {
                'product_id': self.article_product_variant.id,
                'name': self.article_product_variant.name,
                'product_uom_qty': 1,
                'price_unit': self.article_product_variant.lst_price,
            })],
        })
        sale_order.action_confirm()
        self.downpayment_product = self.env['product.product'].create({
            'name': 'Down Payment',
            'available_in_pos': True,
            'type': 'service',
            'taxes_id': [],
        })
        self.pos_config.write({
            'down_payment_product_id': self.downpayment_product.id,
        })
        self.start_pos_tour('PoSDownPaymentFixedTax', login="accountman")

    def test_settle_quotation_delivered_qty(self):
        """ Test if a quotation (unconfirmed sale order) is settled in the PoS, the delivered quantity is updated correctly """
        order = self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [odoo.Command.create({'product_id': self.item_product_variant.id})],
        })
        self.start_pos_tour('PoSSettleQuotation', login="accountman")
        self.assertEqual(order.order_line.qty_delivered, 1)

    def test_edit_invoice_with_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        pos_order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_one.id,
            'pricelist_id': self.partner_one.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.item_product_variant.id,
                'price_unit': self.item_product_variant.lst_price,
                'discount': 0.0,
                'qty': 1.0,
                'tax_ids': [],
                'price_subtotal': self.item_product_variant.lst_price,
                'price_subtotal_incl': self.item_product_variant.lst_price,
            })],
            'amount_total': self.item_product_variant.lst_price,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}'
        })

        # generate an invoice for pos order
        res = pos_order.action_pos_order_invoice()
        self.assertIn('res_id', res, "Invoice should be created")
        self.assertEqual(res['res_id'], pos_order.account_move.id)

        invoice = pos_order.account_move
        self.assertEqual(invoice.state, 'posted')

        # when clicking on cancel button
        invoice.button_draft()
        self.assertEqual(invoice.state, 'draft')
        invoice.button_cancel()
        self.assertEqual(invoice.state, 'cancel')

        # when clicking on confirm button
        invoice.button_draft()
        self.assertEqual(invoice.state, 'draft')
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')
