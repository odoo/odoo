
from openerp.tests import common


class TestWorkOrderProcess(common.TransactionCase):

    def setUp(self):
        super(TestWorkOrderProcess, self).setUp()
        self.MrpProductProduce = self.env['mrp.product.produce']
        self.Product = self.env['product.product']
        self.Lot = self.env['stock.production.lot']
        self.StockMoveLot = self.env['stock.move.lots']
        self.MrpBom = self.env['mrp.bom']
        self.MrpBomLine = self.env['mrp.bom.line']
        self.Inventory = self.env['stock.inventory']
        self.InventoryLine = self.env['stock.inventory.line']
        self.source_location_id = self.ref('stock.stock_location_14')


    def test_00_workorder_process(self):
        """ Testing consume quants and produced quants with workorder """

        # Create manufacturing order

        dining_table = self.env.ref("mrp.product_product_computer_desk")
        product_table_sheet = self.env.ref('mrp.product_product_computer_desk_head')
        product_table_leg = self.env.ref('mrp.product_product_computer_desk_leg')
        product_bolt = self.env.ref('mrp.product_product_computer_desk_bolt')

        production_table = self.env['mrp.production'].create({
            'product_id': dining_table.id,
            'product_qty': 1.0,
            'product_uom_id': dining_table.uom_id.id,
            'bom_id': self.ref("mrp.mrp_bom_desk")})

        # Set tracking lot on finish and consume products.
        dining_table.tracking = 'lot'
        product_table_sheet.tracking = 'lot'
        product_table_leg.tracking = 'lot'
        product_bolt.tracking = "lot"

        # Initial inventory of product sheet, lags and bolt
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
            'location_id': self.source_location_id})
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_table_leg.id,
            'product_uom_id': product_table_leg.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_leg.id,
            'location_id': self.source_location_id})
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_bolt.id,
            'product_uom_id': product_bolt.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_bolt.id,
            'location_id': self.source_location_id})
        inventory.action_done()

        # Create work order
        production_table.button_plan()
        # Check Work order created or not
        self.assertEqual(len(production_table.workorder_ids), 3, "Workorder should be created 3 instead of %s"%(len(production_table.workorder_ids)))

        # ---------------------------------------------------------
        # Process all workorder and check it state.
        # ----------------------------------------------------------

        workorders = production_table.workorder_ids
        self.assertEqual(workorders[0].state, 'ready', "First workorder state should be ready.")
        self.assertEqual(workorders[1].state, 'pending', "Workorder state should be pending.")
        self.assertEqual(workorders[2].state, 'pending', "Workorder state should be pending.")

        # --------------------------------------------------------------
        # Process cutting operation...
        # ---------------------------------------------------------

        finished_lot =self.env['stock.production.lot'].create({'product_id': production_table.product_id.id})
        workorders[0].write({'final_lot_id': finished_lot.id})
        workorders[0].button_start()
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

        finish_move = production_table.move_finished_ids.filtered(lambda x : x.product_id.id == dining_table.id)

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

        # This behaviour was changed
        #self.assertEqual(production_table.state, 'done', "Production order should be in done state.")

        # ----------------------------------------
        # Check consume quants and produce quants.
        # ----------------------------------------

        self.assertEqual(sum(move_table_sheet.quant_ids.mapped('qty')) , 1, "Wrong quantity of consumed product %s"% move_table_sheet.product_id.name)
        self.assertEqual(sum(move_leg.quant_ids.mapped('qty')), 4, "Wrong quantity of consumed product %s"% move_leg.product_id.name)
        self.assertEqual(sum(move_table_bolt.quant_ids.mapped('qty')), 4, "Wrong quantity of consumed product %s"% move_table_bolt.product_id.name)

        consume_quants = move_table_sheet.quant_ids + move_leg.quant_ids + move_table_bolt.quant_ids

        # Check for produced quant correctly linked with consumed quants or not. 

        finish_move = production_table.move_finished_ids.filtered(lambda x : x.product_id.id == dining_table.id)
        finished_quant = finish_move.quant_ids[0]
        for quant in consume_quants:
            self.assertEqual(len(quant.produced_quant_ids), 1, "Wrong produced quants on consumed quant.")
            self.assertEqual(quant.produced_quant_ids[0].lot_id.id, finished_lot.id, "Wrong produced quant lot on consumed quant.")
            self.assertEqual(quant.produced_quant_ids[0].id, finished_quant.id, "Wrong produced quants of consume material.")

        # ------------------------------------------
        # Check finished quants with consumed quant.
        # ------------------------------------------

        self.assertEqual(finished_quant.consumed_quant_ids.ids, consume_quants.ids, "Wrong consume quants on produce quants")

    def test_01_without_workorder(self):
        """ Testing consume quants and produced quants without workorder """
        unit = self.ref("product.product_uom_unit")
        custom_laptop = self.env.ref("product.product_product_27")

        def create_product(name, uom_id):
            return self.Product.create({
                'name': name,
                'type': 'product',
                'tracking': 'lot',
                'uom_id': uom_id,
                'uom_po_id': uom_id})

        def create_bom_lines(bom_id, product_id, qty, uom_id):
            self.MrpBomLine.create({
                'product_id': product_id,
                'product_qty': qty,
                'bom_id': bom_id,
                'product_uom_id': uom_id})

        custom_laptop.tracking = 'lot'

        # Create new product charger and keybord
        # --------------------------------------

        product_charger = create_product('Charger', unit)
        product_keybord = create_product('Usb Keybord', unit)

        # Create bill of material for customized laptop.

        bom_custom_laptop = self.MrpBom.create({
                'product_tmpl_id': custom_laptop.product_tmpl_id.id,
                'product_qty': 10,
                'product_uom_id': unit})
        create_bom_lines(bom_custom_laptop.id, product_charger.id, 20, unit)
        create_bom_lines(bom_custom_laptop.id, product_keybord.id, 20, unit)

        # Create production order for customize laptop.

        mo_custom_laptop = self.env['mrp.production'].create({
            'product_id': custom_laptop.id,
            'product_qty': 10,
            'product_uom_id': unit,
            'bom_id': bom_custom_laptop.id})

        # Assign component to production order.
        mo_custom_laptop.action_assign()

        # Check production order status of availablity
        self.assertEqual(mo_custom_laptop.availability, 'waiting', "Production order should be in waiting state.")

        # --------------------------------------------------
        # Set inventory for rawmaterial charger and keybord
        # --------------------------------------------------


        lot_charger = self.Lot.create({'product_id': product_charger.id})
        lot_keybord = self.Lot.create({'product_id': product_keybord.id})
        inventory = self.Inventory.create({
            'name': 'Inventory Product Table',
            'filter': 'partial'})
        inventory.prepare_inventory()
        self.assertFalse(inventory.line_ids, "Inventory line should not created.")
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_charger.id,
            'product_uom_id': product_charger.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_charger.id,
            'location_id': self.source_location_id})
        self.InventoryLine.create({
            'inventory_id': inventory.id,
            'product_id': product_keybord.id,
            'product_uom_id': product_keybord.uom_id.id,
            'product_qty': 20,
            'prod_lot_id': lot_keybord.id,
            'location_id': self.source_location_id})
        inventory.action_done()

        # Check consumed move status
        mo_custom_laptop.action_assign()
        self.assertEqual( mo_custom_laptop.availability, 'assigned', "Production order should be in assigned state.")

        # Check current status of raw materials.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.product_uom_qty, 20, "Wrong consume quantity of raw material %s"% (move.product_id.name))
            self.assertEqual(move.quantity_done, 0, "Wrong produced quantity on raw material %s"% (move.product_id.name))

        # -----------------
        # Start production
        # -----------------

        # Produce 6 Unit of custom laptop will consume ( 12 Unit of keybord and 12 Unit of charger)

        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        product_consume = self.MrpProductProduce.with_context(context).create({'product_qty': 6.00})
        laptop_lot_001 = self.Lot.create({'product_id': custom_laptop.id})
        product_consume.lot_id = laptop_lot_001.id
        product_consume.consume_line_ids.write({'quantity_done': 12})
        product_consume.do_produce()

        # Check consumed move after produce 6 quantity of customized laptop.
        for move in mo_custom_laptop.move_raw_ids:
            self.assertEqual(move.quantity_done, 12, "Wrong produced quantity on raw material %s"% (move.product_id.name))
        self.assertEqual(len(mo_custom_laptop.move_raw_ids), 2, "Wrong raw material moves of production order.")
        mo_custom_laptop.post_inventory()
        self.assertEqual(len(mo_custom_laptop.move_raw_ids), 4, "Wrong raw material moves of production order.")

        # Check done move and confirmed move quantity.

        charger_done_move = mo_custom_laptop.move_raw_ids.filtered(lambda x : x.product_id.id == product_charger.id and x.state == 'done')
        keybord_done_move = mo_custom_laptop.move_raw_ids.filtered(lambda x : x.product_id.id == product_keybord.id and x.state == 'done')
        self.assertEquals(charger_done_move.product_uom_qty, 12, "Wrong consumed raw material charger.")
        self.assertEquals(keybord_done_move.product_uom_qty, 12, "Wrong consumed raw material keybord")

        # Produce remaining 4 quantity
        # ----------------------------

        # Produce 4 Unit of custom laptop will consume ( 8 Unit of keybord and 8 Unit of charger).
        context = {"active_ids": [mo_custom_laptop.id], "active_id": mo_custom_laptop.id}
        product_consume = self.MrpProductProduce.with_context(context).create({'product_qty': 4.00})
        laptop_lot_002 = self.Lot.create({'product_id': custom_laptop.id})
        product_consume.lot_id = laptop_lot_002.id
        self.assertEquals(len(product_consume.consume_line_ids), 2, "Wrong lots linked with move.")
        product_consume.consume_line_ids.write({'quantity_done': 8})
        product_consume.do_produce()
        charger_move = mo_custom_laptop.move_raw_ids.filtered(lambda x : x.product_id.id == product_charger.id and x.state != 'done')
        keybord_move = mo_custom_laptop.move_raw_ids.filtered(lambda x : x.product_id.id == product_keybord.id and x.state !='done')
        self.assertEquals(charger_move.quantity_done, 8, "Wrong consumed quantity of %s"% charger_move.product_id.name)
        self.assertEquals(keybord_move.quantity_done, 8, "Wrong consumed quantity of %s"% keybord_move.product_id.name)

        # Post Inventory of production order.
        mo_custom_laptop.post_inventory()

        raw_moves_state = any(move.state != 'done' for move in mo_custom_laptop.move_raw_ids)
        finsh_moves_state = any(move.state != 'done' for move in mo_custom_laptop.move_finished_ids)
        self.assertFalse(raw_moves_state, "Wrong state in consumed moves of production order.")
        self.assertFalse(finsh_moves_state, "Wrong state in consumed moves of production order.")

        # Finished move quants of production order

        finshed_quant_lot_001 =  mo_custom_laptop.move_finished_ids.filtered(lambda x : x.product_id.id == custom_laptop.id and x.product_uom_qty==6).mapped('quant_ids')
        finshed_quant_lot_002 =  mo_custom_laptop.move_finished_ids.filtered(lambda x : x.product_id.id == custom_laptop.id and x.product_uom_qty==4).mapped('quant_ids')

        # --------------------------------
        # Check consume and produce quants
        # --------------------------------

        # Check consumed quants of lot2

        for consume_quant in finshed_quant_lot_001[0].consumed_quant_ids:
            self.assertEqual(consume_quant.qty, 12, "Wrong quantity of quants of consume quants")
            self.assertEqual(consume_quant.produced_quant_ids[0].lot_id.id , finshed_quant_lot_001[0].lot_id.id , "Wrong produced quant lot on consume quants")
            self.assertEqual(consume_quant.produced_quant_ids[0].id , finshed_quant_lot_001[0].id , "Wrong produced quant on consume quants")

        self.assertEqual(len(finshed_quant_lot_001[0].consumed_quant_ids), 2, "Wrong consumed quant linked with produced quant for lot %s "%laptop_lot_001.name)

        # Check consumed quants of lot2

        # TODO : Need to check why consumed quants not linked.
        # Check total no of quants linked with produced quants.

        self.assertEqual(len(finshed_quant_lot_002[0].consumed_quant_ids), 2, "Wrong consumed quant linked with produced quant for lot %s "%laptop_lot_002.name)

        for consume_quant in finshed_quant_lot_002[0].consumed_quant_ids:
            self.assertEqual(consume_quant.qty, 8, "Wrong quantity of quants of consume quants")
            self.assertEqual(consume_quant.produced_quant_ids[0].lot_id.id , finshed_quant_lot_002[0].lot_id.id , "Wrong produced quant lot on consume quants")
            self.assertEqual(consume_quant.produced_quant_ids[0].id , finshed_quant_lot_002[0].id , "Wrong produced quant on consume quants")


        # Check total quantity consumed of charger, keybord
        # --------------------------------------------------

        charger_quants = mo_custom_laptop.move_raw_ids.filtered(lambda x : x.product_id.id == product_charger.id and x.state == 'done').mapped('quant_ids')
        keybord_moves = mo_custom_laptop.move_raw_ids.filtered(lambda x : x.product_id.id == product_keybord.id and x.state == 'done').mapped('quant_ids')


        self.assertEqual(sum(charger_quants.mapped('qty')) , 20 , "Wrong consumed quants quantity of charger.")
        self.assertEqual(sum(keybord_moves.mapped('qty')) , 20 , "Wrong consumed quants quantity of keybord.")