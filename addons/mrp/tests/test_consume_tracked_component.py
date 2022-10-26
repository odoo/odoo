from odoo.tests import tagged
from odoo.addons.mrp.tests.common_consume_tracked_component import TestConsumeTrackedComponentCommon

@tagged('post_install', '-at_install')
class TestConsumeTrackedComponent(TestConsumeTrackedComponentCommon):

    def test_option_disabled_and_qty_available(self):
        """
        Option disabled, qty available
        -> Not Tracked components are fully consumed
        -> Tracked components are only consumed on button_mark_done trigger
        """

        self.picking_type.use_auto_consume_components_lots = False

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

        #Quantities are fully reserved (stock.move state is available)
        mo_all.action_assign()
        for mov in mo_all.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.reserved_availability, "Reserved quantity shall be equal to To Consume quantity.")

        #Test for Serial Product
        self.executeConsumptionTriggers(mo_serial)
        self.executeConsumptionTriggers(mo_none)
        self.executeConsumptionTriggers(mo_lot)
        for mov in mo_all.move_raw_ids:
            if mov.has_tracking == 'none' or mov.raw_material_production_id.state == 'done':
                self.assertEqual(mov.product_qty, mov.quantity_done, "Done quantity shall be equal to To Consume quantity.")
            else:
                self.assertEqual(0, mov.quantity_done, "Done quantity shall be equal to 0.")

    def test_option_enabled_and_qty_available(self):
        """
        Option enabled, qty available
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

        #Quantities are fully reserved (stock.move state is available)
        mo_all.action_assign()
        for mov in mo_all.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.reserved_availability, "Reserved quantity shall be equal to To Consume quantity.")

        self.executeConsumptionTriggers(mo_serial)
        self.executeConsumptionTriggers(mo_none)
        self.executeConsumptionTriggers(mo_lot)
        for mov in mo_all.move_raw_ids:
            self.assertEqual(mov.product_qty, mov.quantity_done, "Done quantity shall be equal to To Consume quantity.")

    def test_option_enabled_and_qty_not_available(self):
        """
        Option enabled, qty not available
        -> Not Tracked components are fully consumed
        -> Tracked components are not consumed
        """

        mo_none = self.create_mo(self.mo_none_tmpl, self.DEFAULT_TRIGGERS_COUNT)
        mo_serial = self.create_mo(self.mo_serial_tmpl, self.SERIAL_TRIGGERS_COUNT)
        mo_lot = self.create_mo(self.mo_lot_tmpl, self.DEFAULT_TRIGGERS_COUNT)

        mo_all = mo_none + mo_serial + mo_lot
        mo_all.action_confirm()

        #Quantities are not reserved at all (stock.move state is confirmed)
        mo_all.action_assign()
        for mov in mo_all.move_raw_ids:
            self.assertEqual(0, mov.reserved_availability, "Reserved quantity shall be equal to 0.")

        self.executeConsumptionTriggers(mo_serial)
        self.executeConsumptionTriggers(mo_none)
        self.executeConsumptionTriggers(mo_lot)

        for mov in mo_all.move_raw_ids:
            if mov.has_tracking == 'none':
                self.assertEqual(mov.product_qty, mov.quantity_done, "Done quantity shall be equal to To Consume quantity.")
            else:
                self.assertEqual(0, mov.quantity_done, "Done quantity shall be equal to To Consume quantity.")

    def test_option_enabled_and_qty_partially_available(self):
        """
        Option enabled, qty partially available
        -> Not Tracked components are fully consumed
        -> Tracked components are partially consumed
        """

        #update BoM serial component qty
        self.bom_none_lines[2].product_qty = 2
        self.bom_serial_lines[2].product_qty = 2
        self.bom_lot_lines[2].product_qty = 2

        raw_none_qty = 2
        raw_tracked_qty = 1

        quant = self.create_quant(self.raw_none, raw_none_qty)
        quant |= self.create_quant(self.raw_lot, raw_tracked_qty)
        quant |= self.create_quant(self.raw_serial, raw_tracked_qty)
        quant.action_apply_inventory()

        #We must create & process each MO at once as we must assign quants for each individually
        def testUnit(mo_tmpl, serialTrigger=None):
            mo = self.create_mo(mo_tmpl, 1)
            mo.action_confirm()

            #Quantities are partially reserved (stock.move state is partially_available)
            mo.action_assign()
            for mov in mo.move_raw_ids:
                if mov.has_tracking == "none":
                    self.assertEqual(raw_none_qty, mov.reserved_availability, "Reserved quantity shall be equal to " + str(raw_none_qty)+ ".")
                else:
                    self.assertEqual(raw_tracked_qty, mov.reserved_availability, "Reserved quantity shall be equal to " + str(raw_tracked_qty)+ ".")

            if serialTrigger is None:
                self.executeConsumptionTriggers(mo)
            elif serialTrigger == 1:
                mo.qty_producing = mo.product_qty
                mo._onchange_producing()
            elif serialTrigger == 2:
                mo.action_generate_serial()

            for mov in mo.move_raw_ids:
                if mov.has_tracking == "none":
                    self.assertEqual(mov.product_qty, mov.quantity_done, "Done quantity shall be equal to To Consume quantity.")
                else:
                    self.assertEqual(raw_tracked_qty, mov.quantity_done, "Done quantity shall be equal to " + str(raw_tracked_qty)+ ".")
            mo.action_cancel()

        testUnit(self.mo_none_tmpl)
        testUnit(self.mo_lot_tmpl)
        testUnit(self.mo_serial_tmpl, 1)
        testUnit(self.mo_serial_tmpl, 2)
