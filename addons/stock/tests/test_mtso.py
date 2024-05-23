from addons.stock.tests.test_old_rules import TestOldRules

""" TODO
    Pull & MTSO routes & rules (single vs multi-step)
    Product "Template" for inheritance
    Easy Quant on != loc utility (full vs partial assign)
"""


class TestStockMtso(TestOldRules):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        #   cls.ProductObj = cls.env['product.product']
        #   cls.UomObj = cls.env['uom.uom']
        #   cls.PartnerObj = cls.env['res.partner']
        #   cls.ModelDataObj = cls.env['ir.model.data']
        #   cls.StockPackObj = cls.env['stock.move.line']
        #   cls.StockQuantObj = cls.env['stock.quant']
        #   cls.PickingObj = cls.env['stock.picking']
        #   cls.MoveObj = cls.env['stock.move']
        #   cls.LotObj = cls.env['stock.lot']
        #   cls.StockLocationObj = cls.env['stock.location']

        # Products: P, M, I, Raw I
        #   cls.productA
        #   cls.productB
        #   cls.productC
        #   cls.productD
        #   cls.productE

        # WH: 1s, 2s, 3s
        # cls.warehouse_1 = cls.env['stock.warehouse'].create({
            # 'name': 'Base Warehouse',
            # 'reception_steps': 'one_step',
            # 'delivery_steps': 'ship_only',
            # 'code': 'BWH'})
        # cls.warehouse_2_steps  # pull
        # cls.warehouse_3_steps  # pull
        #For purchase :
        # Partner
        # cls.partner_1 = cls.env['res.partner'].create({
            # 'name': 'Julia Agrolait',
            # 'email': 'julia@agrolait.example.com',
        # })

        # Route MTSO: route MTO:>rules.procure_method = mts_else_mto
        route_mto = cls.warehouse_1.mto_pull_id.route_id
        for r in route_mto.rule_ids:
             r.procure_method = 'mts_else_mto'
        cls.route_mtso = route_mto

        # self.env['stock.quant']._update_available_quantity(prod, location, qty, lot_id=...)

""" FROM sale_mrp """
    # def test_mtso_partial_availability(self):
        # """When a MO is created from a SO through MTSO with partially available stock :
        # Ensure the validation of the MO update the reserved value in the out picking rather
            # than overwriting it with the produced value in order to fulfill the picking.
        # When MO is not done AND product is not available in stock, increase of demand in SO should update existing MO.
        # Either we have multiple sources for the same product, the same move is updated in the out picking. (until it's picked)
        # """
        # route_manufacture = self.company_data['default_warehouse'].manufacture_pull_id.route_id.id
        # route_mto = self.company_data['default_warehouse'].mto_pull_id.route_id.id
        # self.uom_unit = self.env.ref('uom.product_uom_unit')

        # # Create finished product
        # finished_product = self.env['product.product'].create({
            # 'name': 'Product M',
            # 'type': 'product',
            # 'route_ids': [(4, route_mto), (4, route_manufacture)],
        # })

        # def assert_mo_count(count=1):
            # self.assertEqual(len(self.MrpProduction.search([('product_id', '=', finished_product.id)])), count)

        # product_raw = self.env['product.product'].create({
            # 'name': 'raw M',
            # 'type': 'consu',
        # })

        # # Create bom for finish product
        # self.env['mrp.bom'].create({
            # 'product_id': finished_product.id,
            # 'product_tmpl_id': finished_product.product_tmpl_id.id,
            # 'product_uom_id': self.env.ref('uom.product_uom_unit').id,
            # 'product_qty': 1.0,
            # 'type': 'normal',
            # 'bom_line_ids': [(5, 0), (0, 0, {'product_id': product_raw.id})]
        # })

        # # Set an available qty for 'Product M'
        # self.Quant.create({
            # 'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            # 'product_id': finished_product.id,
            # 'inventory_quantity': 4,
        # }).action_apply_inventory()
        # self.assertEqual(float_compare(finished_product.free_qty, 4, precision_rounding=2), 0)

        # # Create sale order
        # sale_form = Form(self.env['sale.order'])
        # sale_form.partner_id = self.env['res.partner'].create({'name': 'Partner'})
        # with sale_form.order_line.new() as line:
            # line.name = finished_product.name
            # line.product_id = finished_product
            # line.product_uom_qty = 7.0
            # line.product_uom = self.uom_unit
            # line.price_unit = 2.0
        # sale_order = sale_form.save()

        # sale_order.action_confirm()
        # delivery = sale_order.picking_ids
        # mo = self.MrpProduction.search([('product_id', '=', finished_product.id)])
        # assert_mo_count()

        # self.assertEqual(len(delivery.move_ids), 1)
        # self.assertEqual(float_compare(delivery.move_ids[0].quantity, 4, precision_rounding=2), 0)
        # self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 7, precision_rounding=2), 0)
        # self.assertEqual(float_compare(mo.product_qty, 3, precision_rounding=2), 0)

        # # Increase of initial demand in SO should update existing picking & MO (MO not done, Qty not available)
        # sale_order.order_line[0].product_uom_qty = 10.0
        # self.assertEqual(len(delivery.move_ids), 1)
        # self.assertEqual(float_compare(delivery.move_ids[0].quantity, 4, precision_rounding=2), 0)  # Available qty didn't changed
        # self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 10, precision_rounding=2), 0)
        # assert_mo_count()
        # self.assertEqual(float_compare(mo.product_qty, 6, precision_rounding=2), 0)

        # # Update product available Qty (+2), increase SO demand (+2), picking DO update, MO DOES NOT update (MO not done, Qty available)
        # self.Quant.create({
            # 'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            # 'product_id': finished_product.id,
            # 'inventory_quantity': 2,
        # }).action_apply_inventory()
        # self.assertEqual(float_compare(finished_product.free_qty, 2, precision_rounding=2), 0)

        # sale_order.order_line[0].product_uom_qty = 12.0
        # self.assertEqual(len(delivery.move_ids), 1)
        # self.assertEqual(float_compare(delivery.move_ids[0].quantity, 6, precision_rounding=2), 0)
        # self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 12, precision_rounding=2), 0)
        # assert_mo_count()
        # self.assertEqual(float_compare(mo.product_qty, 6, precision_rounding=2), 0)  # Increased demand does not affect MO as qty is available in stock

        # mo.button_mark_done()
        # self.assertEqual(mo.state, 'done')
        # self.assertEqual(float_compare(delivery.move_ids[0].quantity, 12, precision_rounding=2), 0)


        # # Increase SO demand creates new MO and update existing picking move (MO done, Qty not available)
        # sale_order.order_line[0].product_uom_qty = 15.0
        # self.assertEqual(len(delivery.move_ids), 1)
        # self.assertEqual(float_compare(delivery.move_ids[0].quantity, 12, precision_rounding=2), 0)
        # self.assertEqual(float_compare(delivery.move_ids[0].product_qty, 15, precision_rounding=2), 0)
        # assert_mo_count(2)
        # mo2 = self.MrpProduction.search([('product_id', '=', finished_product.id)]) - mo
        # self.assertEqual(float_compare(mo.product_qty, 6, precision_rounding=2), 0)  # First MO not affected as it's done
        # self.assertEqual(float_compare(mo2.product_qty, 3, precision_rounding=2), 0)

        # mo2.button_mark_done()
        # self.assertEqual(mo2.state, 'done')
        # self.assertEqual(float_compare(delivery.move_ids[0].quantity, 15, precision_rounding=2), 0)
""" FROM sale_stock """
    # def test_mtso_and_qty_decreasing(self):
        # """
        # First, confirm a SO that has a line with the MTO route (the product
        # should already be available in stock). Then, decrease the qty on the SO
        # line:
        # - The delivery should be updated
        # - There should not be any other picking
        # """
        # warehouse = self.company_data['default_warehouse']
        # customer_location = self.env.ref('stock.stock_location_customers')
        # mto_route = self.env.ref('stock.route_warehouse0_mto')
        # mto_route.active = True

        # self.product_a.type = 'product'
        # self.env['stock.quant']._update_available_quantity(self.product_a, warehouse.lot_stock_id, 10)

        # so = self.env['sale.order'].create({
            # 'partner_id': self.partner_a.id,
            # 'warehouse_id': warehouse.id,
            # 'order_line': [(0, 0, {
                # 'name': self.product_a.name,
                # 'product_id': self.product_a.id,
                # 'product_uom_qty': 10,
                # 'product_uom': self.product_a.uom_id.id,
                # 'price_unit': 1,
                # 'route_id': mto_route.id,
            # })],
        # })
        # so.action_confirm()
        # self.assertRecordValues(so.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])

        # so.order_line.product_uom_qty = 8
        # self.assertRecordValues(so.picking_ids, [{'location_id': warehouse.lot_stock_id.id, 'location_dest_id': customer_location.id}])
        # self.assertEqual(so.picking_ids.move_ids.product_uom_qty, 8)
