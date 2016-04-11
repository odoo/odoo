
from openerp.addons.mrp.tests.test_mrp_users import TestMrpUsers


class TestWorkOrderProcess(TestMrpUsers):

    def test_00_workorder_process(self):
        self.Inventory = self.env['stock.inventory']
        self.InventoryLine = self.env['stock.inventory.line']
        dining_table = self.env.ref("mrp.product_product_computer_desk")
        self.Lot = self.env['stock.production.lot']
        self.StockMoveLot = self.env['stock.move.lots']
        # Create manufacturing order
        production_table = self.env['mrp.production'].create({
            'product_id': dining_table.id,
            'product_qty': 1.0,
            'product_uom_id': dining_table.uom_id.id,
            'bom_id': self.ref("mrp.mrp_bom_desk")})
        product_table_sheet = self.env.ref('mrp.product_product_computer_desk_head')
        product_table_leg = self.env.ref('mrp.product_product_computer_desk_leg')
        product_bolt = self.env.ref('mrp.product_product_computer_desk_bolt')
        source_location_id = production_table.product_id.property_stock_production.id

        # Set tracking lot on finish and consume product.
        dining_table.trcking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"

        # Initial inventory of product sheet, lags, bolt
        lot_sheet = self.Lot.create({'product_id': product_table_sheet.id})
        lot_leg = self.Lot.create({'product_id': product_table_leg.id})
        lot_bolt = self.Lot.create({'product_id': product_bolt.id})
        inventory = self.Inventory.create({
            'name': 'Inventory Product Table',
            'filter': 'partial'})
        inventory.prepare_inventory()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_table_sheet.id,
            'product_uom_id': product_table_sheet.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_sheet.id,
            'location_id': source_location_id})
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_table_leg.id,
            'product_uom_id': product_table_leg.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_leg.id,
            'location_id': source_location_id})
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_bolt.id,
            'product_uom_id': product_bolt.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_bolt.id,
            'location_id': source_location_id})
        inventory.action_done()

        # Create work order
        production_table.button_plan()
        # Check Work order created or not
        self.assertEqual(len(production_table.work_order_ids), 3, "Workorder should be created 3 instead of %s"%(len(production_table.work_order_ids)))

        # ---------------------------------------------------------
        # Process all workorder and check it state.
        # ----------------------------------------------------------

        workorders = production_table.work_order_ids.sorted(lambda x: x.sequence)
        self.assertEqual(workorders[0].state, 'ready', "First workorder state should be ready.")
        self.assertEqual(workorders[1].state, 'pending', "Workorder state should be pending.")
        self.assertEqual(workorders[2].state, 'pending', "Workorder state should be pending.")

        # --------------------------------------------------------------
        # Process cutting operation...
        # ---------------------------------------------------------

        workorders[0].button_start()
        workorders[0].final_lot_id = self.env['stock.production.lot'].create({'product_id': production_table.product_id.id})
        workorders[0].active_move_lot_ids[0].write({'lot_id': lot_sheet.id, 'quantity_done': 1})
        self.assertEqual(workorders[0].state, 'progress', "First workorder state should be Inprogress.")
        workorders[0].record_production()
        self.assertEqual(workorders[0].state, 'done', "Cutting process should be done.")
        move_table_sheet = production_table.move_raw_ids.filtered(lambda x : x.product_id == product_table_sheet)
        self.assertEqual(move_table_sheet.quantity_done, 1, "Wrong consumed quantity of raw materials.")

        # --------------------------------------------------------------
        # Process drilling operation ...
        # ---------------------------------------------------------

        workorders[1].button_start()
        workorders[1].active_move_lot_ids[0].write({'lot_id': lot_leg.id, 'quantity_done': 4})
        workorders[1].record_production()
        move_leg = production_table.move_raw_ids.filtered(lambda x : x.product_id == product_table_leg)
        self.assertEqual(workorders[1].state, 'done', "Drilling process should be done.")
        self.assertEqual(move_leg.quantity_done, 4, "Wrong consumed quantity of raw materials.")

        # --------------------------------------------------------------
        # Process fitting operation ...
        # ---------------------------------------------------------

        workorders[2].button_start()
        move_lot = workorders[2].active_move_lot_ids[0]
        move_lot.write({'lot_id': lot_bolt.id, 'quantity_done': 4})
        move_table_bolt = production_table.move_raw_ids.filtered(lambda x : x.product_id.id == product_bolt.id)
        workorders[2].record_production()
        self.assertEqual(workorders[2].state, 'done', "Fitting process should done.")
        self.assertEqual(move_table_bolt.quantity_done, 4, "Wrong consumed quantity of raw materials.")

        # -----------------------------------------
        # Post inventory of manufacturing order
        # -----------------------------------------

        self.assertEqual(production_table.state, 'done', "Production order should be in done state.")
