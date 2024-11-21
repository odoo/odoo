import copy

from odoo.exceptions import UserError
from odoo.tests import common, tagged, Form


class TestConsumeComponentCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        """
        The following variables are used in each test to define the number of MO to generate.
        They're also used as a verification in the executeConsumptionTriggers() to see if enough MO were passed to it
        in order to test all the triggers.

        SERIAL : MO's product_tracking is 'serial'
        DEFAULT : MO's product_tracking is 'none' or 'lot'
        AVAILABLE : MO'S raw components are fully available
        """
        super().setUpClass()

        cls.SERIAL_AVAILABLE_TRIGGERS_COUNT = 3
        cls.DEFAULT_AVAILABLE_TRIGGERS_COUNT = 2
        cls.SERIAL_TRIGGERS_COUNT = 2
        cls.DEFAULT_TRIGGERS_COUNT = 1

        cls.manufacture_route = cls.env.ref('mrp.route_warehouse0_manufacture')
        cls.stock_id = cls.env.ref('stock.stock_location_stock').id

        cls.picking_type = cls.env['stock.picking.type'].search([('code', '=', 'mrp_operation')])[0]
        cls.picking_type.use_create_components_lots = True

        # Create Products & Components
        cls.produced_lot = cls.env['product.product'].create({
            'name': 'Produced Lot',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'lot',
            'route_ids': [(4, cls.manufacture_route.id, 0)],
        })
        cls.produced_serial = cls.env['product.product'].create({
            'name': 'Produced Serial',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'serial',
            'route_ids': [(4, cls.manufacture_route.id, 0)],
        })
        cls.produced_none = cls.env['product.product'].create({
            'name': 'Produced None',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'none',
            'route_ids': [(4, cls.manufacture_route.id, 0)],
        })

        cls.raw_lot = cls.env['product.product'].create({
            'name': 'Raw Lot',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'lot',
        })
        cls.raw_serial = cls.env['product.product'].create({
            'name': 'Raw Serial',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'serial',
        })
        cls.raw_none = cls.env['product.product'].create({
            'name': 'Raw None',
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking': 'none',
        })

        cls.raws = [cls.raw_none, cls.raw_lot, cls.raw_serial]

        # Workcenter
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name': 'Assembly Line',
        })

        # BoMs
        cls.bom_none = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.produced_none.product_tmpl_id.id,
            'product_uom_id': cls.produced_none.uom_id.id,
            'consumption': 'flexible',
            'sequence': 1
        })

        cls.bom_none_lines = cls.create_bom_lines(cls.bom_none, cls.raws, [3, 2, 1])

        cls.bom_lot = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.produced_lot.product_tmpl_id.id,
            'product_uom_id': cls.produced_lot.uom_id.id,
            'consumption': 'flexible',
            'sequence': 2
        })

        cls.bom_lot_lines = cls.create_bom_lines(cls.bom_lot, cls.raws, [3, 2, 1])

        cls.bom_serial = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.produced_serial.product_tmpl_id.id,
            'product_uom_id': cls.produced_serial.uom_id.id,
            'consumption': 'flexible',
            'sequence': 1
        })

        cls.bom_serial_lines = cls.create_bom_lines(cls.bom_serial, cls.raws, [3, 2, 1])

        # Manufacturing Orders
        cls.mo_none_tmpl = {
            'product_id': cls.produced_none.id,
            'product_uom_id': cls.produced_none.uom_id.id,
            'product_qty': 1,
            'bom_id': cls.bom_none.id
        }

        cls.mo_lot_tmpl = {
            'product_id': cls.produced_lot.id,
            'product_uom_id': cls.produced_lot.uom_id.id,
            'product_qty': 1,
            'bom_id': cls.bom_lot.id
        }

        cls.mo_serial_tmpl = {
            'product_id': cls.produced_serial.id,
            'product_uom_id': cls.produced_serial.uom_id.id,
            'product_qty': 1,
            'bom_id': cls.bom_serial.id
        }

    @classmethod
    def create_quant(cls, product, qty, offset=0, name="L"):
        i = 1
        if product.tracking == 'serial':
            i, qty = qty, 1
            if name == "L":
                name = "S"

        vals = []
        for x in range(1, i + 1):
            qDict = {
                'location_id': cls.stock_id,
                'product_id': product.id,
                'inventory_quantity': qty,
            }

            if product.tracking != 'none':
                qDict['lot_id'] = cls.env['stock.lot'].create({
                    'name': name + str(offset + x),
                    'product_id': product.id,
                }).id
            vals.append(qDict)

        return cls.env['stock.quant'].create(vals)

    @classmethod
    def create_bom_lines(cls, bom, products, quantities=None):
        if quantities is None:
            quantities = [1 for i in range(len(products))]

        vals = []
        for product, seq in zip(products, range(len(products))):
            vals.append({
                'product_id': product.id,
                'product_qty': quantities[seq],
                'product_uom_id': product.uom_id.id,
                'sequence': seq,
                'bom_id': bom.id,
            })

        return cls.env['mrp.bom.line'].create(vals)

    @classmethod
    def create_mo(cls, template, count):
        vals = []
        for _ in range(count):
            vals.append(copy.deepcopy(template))
        mos = cls.env['mrp.production'].create(vals)
        mos.move_raw_ids.mapped('manual_consumption')
        return mos

    def executeConsumptionTriggers(self, mrp_productions):
        """There's 3 different triggers to test : _onchange_producing(), action_generate_serial(), button_mark_done().

        Depending on the tracking of the final product and the availability of the components,
        only a part of these 3 triggers is available or intended to work.

        This function automatically call and process the appropriate triggers.
        """
        tracking = mrp_productions[0].product_tracking
        sameTracking = True
        for mo in mrp_productions:
            sameTracking = sameTracking and mo.product_tracking == tracking
        self.assertTrue(sameTracking, "MOs passed to the executeConsumptionTriggers method shall have the same product_tracking")

        isSerial = tracking == 'serial'
        isAvailable = all(move.state == 'assigned' for move in mrp_productions.move_raw_ids)
        isComponentTracking = any(move.has_tracking != 'none' for move in mrp_productions.move_raw_ids)

        countOk = True
        length = len(mrp_productions)
        if isSerial:
            if isAvailable:
                countOk = length == self.SERIAL_AVAILABLE_TRIGGERS_COUNT
            else:
                countOk = length == self.SERIAL_TRIGGERS_COUNT
        else:
            if isAvailable:
                countOk = length == self.DEFAULT_AVAILABLE_TRIGGERS_COUNT
            else:
                countOk = length == self.DEFAULT_TRIGGERS_COUNT
        self.assertTrue(countOk, "The number of MOs passed to the executeConsumptionTriggers method does not match the associated TRIGGERS_COUNT")

        mrp_productions[0].qty_producing = mrp_productions[0].product_qty
        mrp_productions[0]._onchange_producing()

        i = 1
        if isSerial:
            mrp_productions[i].action_generate_serial()
            i += 1

        if isAvailable:
            error = False
            try:
                mrp_productions[i].button_mark_done()
            except UserError:
                error = True

            self.assertFalse(error, "Immediate Production shall not raise an error.")


@tagged('post_install', '-at_install')
class TestConsumeComponent(TestConsumeComponentCommon):
    def test_option_enabled_and_qty_available(self):
        """Option enabled, qty available
        -> Not Tracked components are fully consumed
        -> Tracked components are fully consumed
        """

        mo_none = self.create_mo(self.mo_none_tmpl, self.DEFAULT_AVAILABLE_TRIGGERS_COUNT)
        mo_serial = self.create_mo(self.mo_serial_tmpl, self.SERIAL_AVAILABLE_TRIGGERS_COUNT)
        mo_lot = self.create_mo(self.mo_lot_tmpl, self.DEFAULT_AVAILABLE_TRIGGERS_COUNT)

        mo_all = mo_none + mo_serial + mo_lot
        mo_all.action_confirm()

        all_qty = 2 * self.DEFAULT_AVAILABLE_TRIGGERS_COUNT + self.SERIAL_AVAILABLE_TRIGGERS_COUNT

        quant = self.create_quant(self.raw_none, 3*all_qty)
        quant |= self.create_quant(self.raw_lot, 2*all_qty)
        quant |= self.create_quant(self.raw_serial, 1*all_qty)
        quant.action_apply_inventory()

        # Quantities are fully reserved (stock.move state is available)
        mo_all.action_assign()
        for mov in mo_all.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity, "Reserved quantity shall be equal to To Consume quantity.")

        self.executeConsumptionTriggers(mo_serial)
        self.executeConsumptionTriggers(mo_none)
        self.executeConsumptionTriggers(mo_lot)
        for mov in mo_all.move_raw_ids:
            self.assertTrue(mov.picked, "All components should be picked")

    def test_option_enabled_and_qty_not_available(self):
        """Option enabled, qty not available
        -> Not Tracked components are fully consumed
        -> Tracked components are not consumed
        """

        mo_none = self.create_mo(self.mo_none_tmpl, self.DEFAULT_TRIGGERS_COUNT)
        mo_serial = self.create_mo(self.mo_serial_tmpl, self.SERIAL_TRIGGERS_COUNT)
        mo_lot = self.create_mo(self.mo_lot_tmpl, self.DEFAULT_TRIGGERS_COUNT)

        mo_all = mo_none + mo_serial + mo_lot
        mo_all.action_confirm()

        # Quantities are not reserved at all (stock.move state is confirmed)
        mo_all.action_assign()
        for mov in mo_all.move_raw_ids:
            self.assertEqual(0, mov.quantity, "Reserved quantity shall be equal to 0.")

        self.executeConsumptionTriggers(mo_serial)
        self.executeConsumptionTriggers(mo_none)
        self.executeConsumptionTriggers(mo_lot)

        for mov in mo_all.move_raw_ids:
            if mov.has_tracking == 'none':
                self.assertTrue(mov.picked, "components should be picked even without no quantity reserved")
            else:
                self.assertEqual(mov.product_qty, mov.quantity, "Done quantity shall be equal to To Consume quantity.")

    def test_option_enabled_and_qty_partially_available(self):
        """Option enabled, qty partially available
        -> Not Tracked components are fully consumed
        -> Tracked components are partially consumed
        """

        # Update BoM serial component qty
        self.bom_none_lines[2].product_qty = 2
        self.bom_serial_lines[2].product_qty = 2
        self.bom_lot_lines[2].product_qty = 2

        raw_none_qty = 2
        raw_tracked_qty = 1

        quant = self.create_quant(self.raw_none, raw_none_qty)
        quant |= self.create_quant(self.raw_lot, raw_tracked_qty)
        quant |= self.create_quant(self.raw_serial, raw_tracked_qty)
        quant.action_apply_inventory()

        # We must create & process each MO at once as we must assign quants for each individually
        def testUnit(mo_tmpl, serialTrigger=None):
            mo = self.create_mo(mo_tmpl, 1)
            mo.action_confirm()

            #  are partially reserved (stock.move state is partially_available)
            mo.action_assign()
            for mov in mo.move_raw_ids:
                if mov.has_tracking == "none":
                    self.assertEqual(raw_none_qty, mov.quantity, "Reserved quantity shall be equal to " + str(raw_none_qty) + ".")
                else:
                    self.assertEqual(raw_tracked_qty, mov.quantity, "Reserved quantity shall be equal to " + str(raw_tracked_qty) + ".")

            if serialTrigger is None:
                self.executeConsumptionTriggers(mo)
            elif serialTrigger == 1:
                mo_form = Form(mo)
                mo_form.qty_producing = mo_form.product_qty
                mo = mo_form.save()
            elif serialTrigger == 2:
                mo.action_generate_serial()

            for mov in mo.move_raw_ids:
                if mov.has_tracking == "none":
                    self.assertTrue(mov.picked, "non tracked components should be picked")
                else:
                    self.assertEqual(mov.product_qty, mov.quantity, "Done quantity shall be equal to To Consume quantity.")
            mo.action_cancel()

        testUnit(self.mo_none_tmpl)
        testUnit(self.mo_lot_tmpl)
        testUnit(self.mo_serial_tmpl, 1)
        testUnit(self.mo_serial_tmpl, 2)

    def test_tracked_production_2_steps_manufacturing(self):
        """
        Create an MO for a product tracked by SN in 2-steps manufacturing with tracked components.
        Assign a SN to the final product using the auto generation, then validate the pbm picking.
        This test checks that the tracking of components is updated on the MO.
        """
        warehouse = self.env.ref('stock.warehouse0')
        warehouse.manufacture_steps = 'pbm'
        bom = self.bom_serial
        bom.product_id = self.produced_serial
        components = self.bom_serial.bom_line_ids.mapped('product_id')
        lot_1 = self.env['stock.lot'].create({
            'name': 'lot_1',
            'product_id': components[1].id,
            'company_id': self.env.company.id,
        })
        lot_2 = self.env['stock.lot'].create({
            'name': 'SN01',
            'product_id': components[2].id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant']._update_available_quantity(components[0], self.env.ref('stock.warehouse0').lot_stock_id, 3)
        self.env['stock.quant']._update_available_quantity(components[1], self.env.ref('stock.warehouse0').lot_stock_id, 2, lot_id=lot_1)
        self.env['stock.quant']._update_available_quantity(components[2], self.env.ref('stock.warehouse0').lot_stock_id, 1, lot_id=lot_2)
        mo = self.env['mrp.production'].create({
            'product_id': bom.product_id.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        self.assertRecordValues(mo.picking_ids.move_ids, [
            {'quantity': 3.0, 'picked': False, 'lot_ids': []},
            {'quantity': 2.0, 'picked': False, 'lot_ids': lot_1.ids},
            {'quantity': 1.0, 'picked': False, 'lot_ids': lot_2.ids},
        ])
        with Form(mo) as mo_form:
            mo_form.qty_producing = 1.0
        self.assertRecordValues(mo.move_raw_ids, [
            {'should_consume_qty': 3.0, 'quantity': 3.0, 'picked': True, 'lot_ids': []},
            {'should_consume_qty': 2.0, 'quantity': 0.0, 'picked': False, 'lot_ids': []},
            {'should_consume_qty': 1.0, 'quantity': 0.0, 'picked': False, 'lot_ids': []},
        ])
        mo.action_generate_serial()
        self.assertRecordValues(mo.move_raw_ids, [
            {'should_consume_qty': 3.0, 'quantity': 3.0, 'picked': True, 'lot_ids': []},
            {'should_consume_qty': 2.0, 'quantity': 0.0, 'picked': False, 'lot_ids': []},
            {'should_consume_qty': 1.0, 'quantity': 0.0, 'picked': False, 'lot_ids': []},
        ])
        self.assertTrue(mo.lot_producing_id)
        mo.picking_ids.button_validate()
        self.assertRecordValues(mo.move_raw_ids, [
            {'quantity': 3.0, 'picked': True, 'lot_ids': []},
            {'quantity': 2.0, 'picked': False, 'lot_ids': lot_1.ids},
            {'quantity': 1.0, 'picked': False, 'lot_ids': lot_2.ids},
        ])
        mo.move_raw_ids.picked = True
        mo.button_mark_done()
