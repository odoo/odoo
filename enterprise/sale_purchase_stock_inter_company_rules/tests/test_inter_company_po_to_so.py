# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import Command, fields
from odoo.tests import Form, tagged
from .common import TestInterCompanyRulesCommonStock


@tagged('post_install', '-at_install')
class TestInterCompanyPurchaseToSaleWithStock(TestInterCompanyRulesCommonStock):
    def test_01_inter_company_purchase_order_with_stock_picking(self):
        partner = self.env['res.partner'].create({
            'name': 'Odoo',
            'child_ids': [
                (0, 0, {'name': 'Farm 1', 'type': 'delivery'}),
                (0, 0, {'name': 'Farm 2', 'type': 'delivery'}),
                (0, 0, {'name': 'Farm 3', 'type': 'delivery'}),
            ]
        })
        self.company_b.update({'partner_id': partner.id})
        (self.company_b | self.company_a).update({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
        })
        children = partner.child_ids
        warehouses = self.env['stock.warehouse'].sudo().create([
            {
                'name': 'Farm 1 warehouse',
                'code': 'FWH1',
                'company_id': self.company_b.id,
                'partner_id': children[0].id,
            },
            {
                'name': 'Farm 2 warehouse',
                'code': 'FWH2',
                'company_id': self.company_b.id,
                'partner_id': children[1].id,
            },
            {
                'name': 'Farm 3 warehouse',
                'code': 'FWH3',
                'company_id': self.company_b.id,
                'partner_id': children[2].id,
            },
        ])

        def generate_purchase_and_validate_sale_order(first_company, second_company, warehouse_id):
            stock_picking_type = self.env['stock.picking.type'].search(['&', ('warehouse_id', '=', warehouse_id), ('name', '=', 'Receipts')])
            purchase_order = Form(self.env['purchase.order'])
            purchase_order.partner_id = second_company.partner_id
            purchase_order.company_id = first_company
            purchase_order = purchase_order.save()
            purchase_order.picking_type_id = stock_picking_type
            with Form(purchase_order) as po:
                with po.order_line.new() as line:
                    line.name = 'Service'
                    line.product_id = self.product_consultant
                    line.price_unit = 450.0
                    line.discount = 10.0
            purchase_order.with_company(first_company).button_confirm()
            self.validate_generated_sale_order(purchase_order, first_company, second_company)

        for warehouse in warehouses:
            generate_purchase_and_validate_sale_order(self.company_b, self.company_a, warehouse.id)

    def validate_generated_sale_order(self, purchase_order, company, partner):
        """ Validate sale order which has been generated from purchase order
        and test its state, total_amount, product_name and product_quantity.
        """

        # Find related sale order based on client order reference.
        sale_order = self.env['sale.order'].with_company(partner).search([('client_order_ref', '=', purchase_order.name)], limit=1)

        self.assertEqual(sale_order.state, "draft", "sale order should be in draft state.")
        self.assertEqual(sale_order.partner_id, company.partner_id, "Vendor does not correspond to Company %s." % company)
        self.assertEqual(sale_order.company_id, partner, "Applied company in created sale order is incorrect.")
        self.assertEqual(sale_order.amount_total, 465.75, "Total amount is incorrect.")
        self.assertEqual(sale_order.order_line[0].product_id, self.product_consultant, "Product in line is incorrect.")
        self.assertEqual(sale_order.order_line[0].name, 'Service', "Product name is incorrect.")
        self.assertEqual(sale_order.order_line[0].product_uom_qty, 1, "Product qty is incorrect.")
        self.assertEqual(sale_order.order_line[0].price_unit, 450, "Unit Price in line is incorrect.")
        self.assertEqual(sale_order.order_line[0].price_subtotal, 405, "Subtotal in line is incorrect.")
        self.assertTrue(sale_order.partner_shipping_id == purchase_order.picking_type_id.warehouse_id.partner_id, "Partner shipping is incorrect.")

    def test_02_inter_company_sale_purchase_auto_validation(self):
        self.env.user.groups_id += self.env.ref('base.group_multi_currency')
        today = fields.Datetime.today()
        (self.company_b | self.company_a).update({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
            'intercompany_document_state': 'posted',
        })
        supplier = self.env['res.partner'].create({
            'name': 'Blabli car',
            'company_id': False
        })

        mto_route = self.env['stock.route'].with_context(active_test=False).search([('name', '=', 'Replenish on Order (MTO)')])
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')])
        mto_route.active = True

        product_storable = self.env['product.product'].create({
            'name': 'Storable',
            'categ_id': self.env.ref('product.product_category_all').id,
            'is_storable': True,
            'taxes_id': [(6, 0, (self.company_a.account_sale_tax_id + self.company_b.account_sale_tax_id).ids)],
            'supplier_taxes_id': [(6, 0, (self.company_a.account_purchase_tax_id + self.company_b.account_purchase_tax_id).ids)],
            'route_ids': [(6, 0, [buy_route.id, mto_route.id])],
            'company_id': False,
            'seller_ids': [
                (0, 0, {
                    'partner_id': self.company_a.partner_id.id,
                    'min_qty': 1,
                    'price': 250,
                    'company_id': self.company_b.id,
                }),
                (0, 0, {
                    'partner_id': supplier.id,
                    'min_qty': 1,
                    'price': 200,
                    'company_id': self.company_a.id,
                })
            ]
        })

        purchase_order = Form(self.env['purchase.order'].with_company(self.company_b))
        purchase_order.partner_id = self.company_a.partner_id
        purchase_order.company_id = self.company_b
        purchase_order.currency_id = self.company_b.currency_id
        purchase_order = purchase_order.save()

        with Form(purchase_order.with_company(self.company_b)) as po:
            with po.order_line.new() as line:
                line.product_id = product_storable

        purchase_order.date_planned = today + relativedelta(days=7)
        # Confirm Purchase order
        purchase_order.with_company(self.company_b).button_confirm()
        # Check purchase order state should be purchase.
        self.assertEqual(purchase_order.state, 'purchase', 'Purchase order should be in purchase state.')

        sale_order = self.env['sale.order'].with_company(self.company_a).search([
            ('client_order_ref', '=', purchase_order.name),
            ('company_id', '=', self.company_a.id)
        ], limit=1)
        self.assertTrue(sale_order)
        self.assertEqual(len(sale_order.order_line), 1)
        self.assertEqual(sale_order.order_line.product_id, product_storable)
        self.assertEqual(sale_order.commitment_date, today + relativedelta(days=7))
        # Check the MTO purchase, the seller should be the correct one
        po = self.env['purchase.order'].with_company(self.company_a).search([
            ('company_id', '=', self.company_a.id)
        ], limit=1, order='id DESC')
        self.assertTrue(po)
        self.assertEqual(po.partner_id, supplier)
        self.assertEqual(po.order_line.product_id, product_storable)
        self.assertEqual(po.order_line.price_unit, 200)

    def test_03_inter_company_sale_to_purchase_with_stock_picking(self):
        product = self.env['product.product'].create({
            'name': 'Product TEST',
            'is_storable': True
        })

        partner = self.env['res.partner'].create({
            'name': 'Odoo',
            'child_ids': [
                (0, 0, {'name': 'Farm 1', 'type': 'delivery'}),
                (0, 0, {'name': 'Farm 2', 'type': 'delivery'}),
                (0, 0, {'name': 'Farm 3', 'type': 'delivery'}),
            ]
        })
        self.company_b.update({'partner_id': partner.id})
        (self.company_b | self.company_a).update({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
            'intercompany_document_state': 'posted',  # Needed to create the receipt
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.company_b.partner_id.id,
            'user_id': self.res_users_company_a.id,
            'order_line': [
                Command.create({
                    'product_id': product.id,
                    'price_unit': 750.00,
                })
            ]
        })
        sale_order.with_user(self.res_users_company_a).action_confirm()
        picking = sale_order.picking_ids[0]
        picking.move_ids[0].quantity = 1.0
        picking.with_user(self.res_users_company_a).button_validate()

        purchase_order = self.env['purchase.order'].sudo().search([('name', '=', sale_order.client_order_ref), ('company_id', '=', self.company_b.id)])
        self.assertEqual(purchase_order.company_id, self.company_b)
        self.assertEqual(purchase_order.partner_id, self.company_a.partner_id)
        self.assertEqual(purchase_order.order_line.product_id, product)

        new_picking = purchase_order.picking_ids[0]
        self.assertEqual(new_picking.company_id, self.company_b)
        self.assertEqual(new_picking.partner_id, self.company_a.partner_id)
        self.assertEqual(new_picking.product_id, product)

    def test_04_inter_company_putaway_rules(self):
        """
        Check that putaway strategies are correctly applied on tracked products
        when the transaction is updated by an intercompany procedure.
        """
        # with company A:
        self.company_a.update({
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
            'intercompany_document_state': 'posted',  # Needed to create the receipt
        })
        stock_location_a = self.env['stock.warehouse'].search([('company_id', '=', self.company_a.id)], limit=1).lot_stock_id
        shelf_location = self.env['stock.location'].with_company(self.company_a).create({
            'name': 'Shelf',
            'usage': 'internal',
            'location_id': stock_location_a.id,
        })
        self.env["stock.putaway.rule"].with_company(self.company_a).create({
            "location_in_id": stock_location_a.id,
            "location_out_id": shelf_location.id,
            'category_id': self.env.ref('product.product_category_all').id,
        })
        # with company B:
        my_product = self.env['product.product'].with_company(self.company_b).create({
            'name': 'my product',
            'is_storable': True,
            'tracking': 'serial',
            'sale_ok': True,
        })
        my_lot = self.env['stock.lot'].with_company(self.company_b).create({
            'name': 'SN0001',
            'product_id': my_product.id,
        })
        stock_location_b = self.env['stock.warehouse'].search([('company_id', '=', self.company_b.id)], limit=1).lot_stock_id
        self.env['stock.quant'].with_company(self.company_b)._update_available_quantity(my_product, stock_location_b, 1, lot_id=my_lot)
        so = self.env['sale.order'].with_company(self.company_b).create({
                'partner_id': self.company_a.partner_id.id,
                'order_line': [Command.create({
                        'product_id': my_product.id,
                        'price_unit': 100,
                    })
                ]
        })
        so.action_confirm()
        po = self.env['purchase.order'].search([('auto_sale_order_id', '=', so.id)], limit=1)
        # There should be no move lines yet as no reservation could be done, as delivery is not processed yet.
        self.assertFalse(po.picking_ids.move_line_ids)
        # Confirm the delivery created in company B to update the delivery in Company A
        delivery_b = so.picking_ids
        delivery_b.move_line_ids.lot_id = my_lot
        delivery_b.button_validate()
        receipt_a = po.picking_ids
        self.assertEqual(receipt_a.move_line_ids.location_dest_id, shelf_location)
        receipt_a.button_validate()
        self.assertEqual(receipt_a.move_line_ids.location_dest_id, shelf_location)
        self.assertEqual(receipt_a.move_line_ids.lot_id.name, my_lot.name)
        self.assertTrue(receipt_a.move_line_ids.picked)

    def test_05_inter_company_purchase_order_from_so_with_custom_attribute_values(self):
        """
        Check that the custom attribute values are transfered by procurements
        """
        self.company_b.update({
            'intercompany_generate_sales_orders': True,
        })
        self.env['stock.warehouse'].search([('company_id', '=', self.company_a.id)], limit=1).write({'delivery_steps': 'pick_pack_ship'})
        mto_route = self.env['stock.route'].with_context(active_test=False).search([('name', '=', 'Replenish on Order (MTO)')])
        mto_route.rule_ids.procure_method = "make_to_order"
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')])
        mto_route.active = True

        # setup product with customizable attribute value
        product_storable = self.env['product.product'].create({
            'name': 'Storable',
            'is_storable': True,
            'route_ids': [Command.set([buy_route.id, mto_route.id])],
            'company_id': False,
            'seller_ids': [
                Command.create({
                    'partner_id': self.company_b.partner_id.id,
                    'min_qty': 1,
                    'price': 250,
                    'company_id': self.company_a.id,
                }),
            ]
        })
        product_attribute = self.env['product.attribute'].create({
            'name': 'product attribute',
            'display_type': 'radio',
            'create_variant': 'always'
        })
        product_attribute_value = self.env['product.attribute.value'].create({
            'name': 'single product attribute value',
            'is_custom': True,
            'attribute_id': product_attribute.id
        })
        product_attribute_line = self.env['product.template.attribute.line'].create({
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_storable.product_tmpl_id.id,
            'value_ids': [Command.link(product_attribute_value.id)]
        })

        custom_value = "test"

        # create and confirm SO with comp a for a customer
        sale_order = self.env['sale.order'].with_company(self.company_a).create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'COMP1 SO',
                    'product_id': product_storable.id,
                    'product_uom_qty': 1,
                    'product_custom_attribute_value_ids': [
                        Command.create({
                            'custom_product_template_attribute_value_id': product_attribute_line.product_template_value_ids.id,
                            'custom_value': custom_value,
                        })
                    ],
                })
            ],
        })
        sale_order.action_confirm()
        po = self.env['purchase.order'].search([('partner_id', '=', self.company_b.partner_id.id)])
        self.assertTrue(custom_value in po.order_line.display_name)
        po.with_company(self.company_a).button_confirm()
        auto_generated_so = self.env['sale.order'].search([('partner_id', '=', self.company_a.partner_id.id)])
        self.assertRecordValues(auto_generated_so, [{'auto_generated': True, 'auto_purchase_order_id': po.id}])
        self.assertTrue(custom_value in auto_generated_so.order_line.name)
        original_custom_attribute = sale_order.order_line.product_custom_attribute_value_ids
        copied_custom_attribute = auto_generated_so.order_line.product_custom_attribute_value_ids
        self.assertEqual(
            original_custom_attribute.custom_value,
            copied_custom_attribute.custom_value,
        )
        self.assertEqual(
            original_custom_attribute.custom_product_template_attribute_value_id,
            copied_custom_attribute.custom_product_template_attribute_value_id,
        )

    def test_07_inter_company_serial_across_companies(self):
        """ Checks that on a inter-company transfer, the right quants are created/updated in the right locations.
            Follows the trail of a serial-tracked product along the following flow:
            Vendor -> Company A -> Company B -> Customer
        """
        self.env.user.groups_id |= self.env.ref('stock.group_production_lot')
        (self.company_a | self.company_b).write({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
            'intercompany_document_state': 'posted',
        })
        vendor, customer = self.env['res.partner'].create([{
            'name': name,
        } for name in ['Vendor', 'Customer']])
        # Use MTO route to avoid having to deal with manual replenishments
        mto_route = self.env.ref('stock.route_warehouse0_mto')
        mto_route.active = True
        mto_route.rule_ids.procure_method = 'make_to_order'
        buy_route = self.env.ref('purchase_stock.route_warehouse0_buy')

        product = self.env['product.product'].create({
            'is_storable': True,
            'tracking': 'serial',
            'name': 'Cross Serial',
            'company_id': False,
            'seller_ids': [
                Command.create({'partner_id': vendor.id, 'company_id': self.company_a.id}),
                Command.create({'partner_id': self.company_a.partner_id.id, 'company_id': self.company_b.id}),
            ],
            'route_ids': [
                Command.link(mto_route.id),
                Command.link(buy_route.id),
            ]
        })

        # Create a sale order from Company B to the customer
        with Form(self.env['sale.order'].with_company(self.company_b)) as sale_form:
            sale_form.partner_id = customer
            with sale_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 1
            sale_to_customer = sale_form.save()
        sale_to_customer.with_company(self.company_b).action_confirm()
        self.assertEqual(sale_to_customer.purchase_order_count, 1)
        purchase_from_a = sale_to_customer._get_purchase_orders()
        self.assertEqual(purchase_from_a.partner_id, self.company_a.partner_id)
        purchase_from_a.with_company(self.company_b).button_confirm()

        # Company A side.
        sale_to_b = self.env['sale.order'].with_company(self.company_a).search([('client_order_ref', '=', purchase_from_a.name)], limit=1)
        self.assertEqual(sale_to_b.state, 'sale')
        self.assertEqual(sale_to_b.purchase_order_count, 1)
        purchase_from_vendor = sale_to_b._get_purchase_orders()
        purchase_from_vendor.button_confirm()
        receipt_from_vendor = purchase_from_vendor.picking_ids

        # Receive lot from vendor
        lot = self.env['stock.lot'].create({'name': 'lot', 'product_id': product.id})
        with Form(receipt_from_vendor) as receipt_form:
            with receipt_form.move_ids_without_package.edit(0) as move_form:
                move_form.lot_ids = lot
                move_form.quantity = 1
                move_form.picked = True
            receipt_from_vendor = receipt_form.save()
        receipt_from_vendor.button_validate()

        # Transfer lot to Company B
        interco_location = self.env.ref('stock.stock_location_inter_company')
        self.assertEqual(sale_to_b.picking_ids.state, 'assigned')
        self.assertEqual(sale_to_b.picking_ids.move_ids.lot_ids, lot)
        self.assertEqual(sale_to_b.picking_ids.location_dest_id, interco_location)
        sale_to_b.picking_ids.button_validate()
        self.assertEqual(sale_to_b.order_line.qty_delivered, 1)

        # Receive lot from Company A
        self.assertEqual(purchase_from_a.picking_ids.move_ids.lot_ids, lot)
        self.assertEqual(purchase_from_a.picking_ids.location_id, interco_location)
        purchase_from_a.picking_ids.with_company(self.company_b).button_validate()

        # Send lot to Customer
        self.assertEqual(sale_to_customer.picking_ids.state, 'assigned')
        self.assertEqual(sale_to_customer.picking_ids.move_ids.lot_ids, lot)
        sale_to_customer.picking_ids.with_company(self.company_b).button_validate()

        customer_location = self.env.ref('stock.stock_location_customers')
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, interco_location, lot), 0)
        self.assertEqual(self.env['stock.quant']._get_available_quantity(product, customer_location, lot), 1)

    def test_08_dropship_inter_company_vendor_to_customer(self):
        try:
            dropship_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        except ValueError:
            self.skipTest('This test requires the following module: stock_dropshipping')

        (self.company_a | self.company_b).write({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
        })
        vendor, customer = self.env['res.partner'].create([{
            'name': name,
        } for name in ['Vendor', 'Customer']])

        product = self.env['product.product'].create({
            'is_storable': True,
            'tracking': 'serial',
            'name': 'Cross Serial',
            'company_id': False,
            'seller_ids': [
                Command.create({'partner_id': vendor.id, 'company_id': self.company_a.id}),
                Command.create({'partner_id': self.company_a.partner_id.id, 'company_id': self.company_b.id}),
            ],
            'route_ids': [
                Command.link(dropship_route.id),
            ]
        })

        # Create a sale order from Company B to the customer
        with Form(self.env['sale.order'].with_company(self.company_b)) as sale_form:
            sale_form.partner_id = customer
            with sale_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 1
            sale_to_customer = sale_form.save()
        sale_to_customer.with_company(self.company_b).action_confirm()
        self.assertEqual(sale_to_customer.purchase_order_count, 1)
        purchase_from_a = sale_to_customer._get_purchase_orders()
        self.assertEqual(purchase_from_a.partner_id, self.company_a.partner_id)
        purchase_from_a.with_company(self.company_b).button_confirm()
        self.assertEqual(sale_to_customer.dropship_picking_count, 1)
        self.assertEqual(purchase_from_a.dropship_picking_count, 1)

        # Company A side.
        sale_to_b = self.env['sale.order'].with_company(self.company_a).search([('client_order_ref', '=', purchase_from_a.name)], limit=1)
        sale_to_b.with_company(self.company_a).action_confirm()
        self.assertEqual(sale_to_b.purchase_order_count, 1)
        purchase_from_vendor = sale_to_b._get_purchase_orders()
        purchase_from_vendor.button_confirm()
        self.assertEqual(sale_to_b.dropship_picking_count, 1)
        self.assertEqual(purchase_from_vendor.dropship_picking_count, 1)
        dropship_from_vendor = purchase_from_vendor.picking_ids

        # Dropship lot from vendor
        lot = self.env['stock.lot'].create({'name': 'lot', 'product_id': product.id})
        with Form(dropship_from_vendor) as receipt_form:
            with receipt_form.move_ids_without_package.edit(0) as move_form:
                move_form.lot_ids = lot
                move_form.quantity = 1
                move_form.picked = True
            dropship_from_vendor = receipt_form.save()
        dropship_from_vendor.button_validate()

        interco_location = self.env.ref('stock.stock_location_inter_company')
        self.assertEqual(sale_to_b.picking_ids.state, 'done')
        self.assertEqual(sale_to_b.picking_ids.location_dest_id, interco_location)

        # Lot should be preset from Company A
        self.assertEqual(purchase_from_a.picking_ids.move_ids.lot_ids, lot)
        self.assertEqual(purchase_from_a.picking_ids.location_id, interco_location)

    def test_09_dropship_inter_company_other_company_to_customer(self):
        if self.env['ir.module.module']._get('stock_dropshipping').state != 'installed':
            self.skipTest('This test requires the following module: stock_dropshipping')

        dropship_type = self.env['stock.picking.type'].search([('code', '=', 'dropship'), ('company_id', '=', self.company_b.id)])
        (self.company_a | self.company_b).write({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
        })
        vendor, customer = self.env['res.partner'].create([{
            'name': name,
        } for name in ['Vendor', 'Customer']])
        # Avoids issue if mrp_subcontracting is already installed, as there will be two dropships per company, customer & subcontractor
        dropship_type = dropship_type.filtered(lambda pt: pt.default_location_dest_id == customer.property_stock_customer)

        dropship_A2B = self.env['stock.route'].create({
            'name': 'Dropship A -> B',
            'company_id': self.company_b.id,
            'product_selectable': True,
            'rule_ids': [Command.create({
                'name': 'Vendor -> Customers',
                'action': 'buy',
                'picking_type_id': dropship_type.id,
                'location_dest_id': customer.property_stock_customer.id,
                'company_id': self.company_b.id,
            })],
        })
        product = self.env['product.product'].create({
            'is_storable': True,
            'tracking': 'serial',
            'name': 'Cross Serial',
            'company_id': False,
            'seller_ids': [
                Command.create({'partner_id': vendor.id, 'company_id': self.company_a.id}),
                Command.create({'partner_id': self.company_a.partner_id.id, 'company_id': self.company_b.id}),
            ],
            'route_ids': [
                Command.link(dropship_A2B.id),
            ]
        })
        lot = self.env['stock.lot'].create({'name': 'lot', 'product_id': product.id})
        warehouse_a = self.env['stock.warehouse'].search([('company_id', '=', self.company_a.id)], limit=1)
        self.env['stock.quant']._update_available_quantity(product, warehouse_a.lot_stock_id, 1, lot_id=lot)

        # Create a sale order from Company B to the customer
        with Form(self.env['sale.order'].with_company(self.company_b)) as sale_form:
            sale_form.partner_id = customer
            with sale_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 1
            sale_to_customer = sale_form.save()
        sale_to_customer.with_company(self.company_b).action_confirm()
        self.assertEqual(sale_to_customer.purchase_order_count, 1)
        purchase_from_a = sale_to_customer._get_purchase_orders()
        self.assertEqual(purchase_from_a.partner_id, self.company_a.partner_id)
        purchase_from_a.with_company(self.company_b).button_confirm()

        # Company A side, deliver lot to Company B
        sale_to_b = self.env['sale.order'].with_company(self.company_a).search([('client_order_ref', '=', purchase_from_a.name)], limit=1)
        sale_to_b.with_company(self.company_a).action_confirm()
        interco_location = self.env.ref('stock.stock_location_inter_company')
        self.assertEqual(sale_to_b.picking_ids.state, 'assigned')
        self.assertEqual(sale_to_b.picking_ids.location_dest_id, interco_location)
        sale_to_b.with_company(self.company_a).picking_ids.button_validate()

        # Lot should be preset from Company A
        self.assertEqual(purchase_from_a.picking_ids.move_ids.lot_ids, lot)
        self.assertEqual(purchase_from_a.picking_ids.location_id, interco_location)

    def test_dropship_third_company_to_customer(self):
        """ Checks that when the flow is the following :
            Comapny C -> Company B -> Company A -> Customer with all dropships, the
            delivered quantity on the sale order from B to C is updated correctly
        """
        try:
            dropship_route = self.env.ref('stock_dropshipping.route_drop_shipping')
        except ValueError:
            self.skipTest('This test requires the following module: stock_dropshipping')

        company = self._create_company(name='company_3')
        company_c = self.collect_company_accounting_data(company)['company']
        (self.company_a | self.company_b | company_c).write({
            'intercompany_generate_sales_orders': True,
            'intercompany_generate_purchase_orders': True,
            'intercompany_sync_delivery_receipt': True,
        })

        customer = self.env['res.partner'].create({
            'name': 'Customer',
        })
        product = self.env['product.product'].create({
            'is_storable': True,
            'name': 'cross comp dp prod',
            'company_id': False,
            'seller_ids': [
                Command.create({'partner_id': company_c.partner_id.id, 'company_id': self.company_b.id}),
                Command.create({'partner_id': self.company_b.partner_id.id, 'company_id': self.company_a.id}),
            ],
        })

        # Required for `route_id` to be visible in the view
        self.env.user.groups_id += self.env.ref('stock.group_adv_location')

        # Set quantity in company C
        warehouse_c = self.env['stock.warehouse'].search([('company_id', '=', company_c.id)], limit=1)
        self.env['stock.quant']._update_available_quantity(product, warehouse_c.lot_stock_id, 1)

        # Create a sale order from Company A to the customer and confirm PO
        with Form(self.env['sale.order'].with_company(self.company_a)) as sale_form:
            sale_form.partner_id = customer
            with sale_form.order_line.new() as line:
                line.product_id = product
                line.product_uom_qty = 1
                line.route_id = dropship_route
            sale_to_customer = sale_form.save()
        sale_to_customer.with_company(self.company_a).action_confirm()
        purchase_from_b = sale_to_customer._get_purchase_orders()
        purchase_from_b.with_company(self.company_a).button_confirm()

        # Company B side : confirm SO and PO
        sale_to_a = self.env['sale.order'].with_company(self.company_b).search([('client_order_ref', '=', purchase_from_b.name)], limit=1)
        with Form(sale_to_a) as sale_form:
            with sale_form.order_line.edit(0) as line:
                line.route_id = dropship_route
            sale_to_a = sale_form.save()
        sale_to_a.with_company(self.company_b).action_confirm()
        purchase_from_c = sale_to_a._get_purchase_orders()
        purchase_from_c.with_company(self.company_b).button_confirm()

        # Company C side : confirm SO and validate delivery
        sale_to_b = self.env['sale.order'].with_company(company_c).search([('client_order_ref', '=', purchase_from_c.name)], limit=1)
        sale_to_b.with_company(company_c).action_confirm()
        sale_to_b.with_company(company_c).picking_ids.button_validate()

        # Back to company B : validate dropship and check that delivered quantity is 1
        purchase_from_c.with_company(self.company_b).picking_ids.button_validate()
        self.assertEqual(sale_to_a.order_line.qty_delivered, 1)
