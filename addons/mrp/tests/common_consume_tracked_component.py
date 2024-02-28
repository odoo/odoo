import copy

from odoo.exceptions import UserError
from odoo.tests import common, Form
from odoo.tools import float_is_zero

class TestConsumeTrackedComponentCommon(common.TransactionCase):

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
        cls.picking_type.use_auto_consume_components_lots = True

        #Create Products & Components
        cls.produced_lot = cls.env['product.product'].create({
            'name': 'Produced Lot',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking' : 'lot',
            'route_ids': [(4, cls.manufacture_route.id, 0)],
        })
        cls.produced_serial = cls.env['product.product'].create({
            'name': 'Produced Serial',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking' : 'serial',
            'route_ids': [(4, cls.manufacture_route.id, 0)],
        })
        cls.produced_none = cls.env['product.product'].create({
            'name': 'Produced None',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking' : 'none',
            'route_ids': [(4, cls.manufacture_route.id, 0)],
        })

        cls.raw_lot = cls.env['product.product'].create({
            'name': 'Raw Lot',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking' : 'lot',
        })
        cls.raw_serial = cls.env['product.product'].create({
            'name': 'Raw Serial',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking' : 'serial',
        })
        cls.raw_none = cls.env['product.product'].create({
            'name': 'Raw None',
            'type': 'product',
            'categ_id': cls.env.ref('product.product_category_all').id,
            'tracking' : 'none',
        })

        cls.raws = [cls.raw_none, cls.raw_lot, cls.raw_serial]

        #Workcenter
        cls.workcenter = cls.env['mrp.workcenter'].create({
            'name' : 'Assembly Line',
        })

        #BoMs
        cls.bom_none = cls.env['mrp.bom'].create({
            'product_tmpl_id' : cls.produced_none.product_tmpl_id.id,
            'product_uom_id' : cls.produced_none.uom_id.id,
            'consumption' : 'flexible',
            'sequence' : 1
        })

        cls.bom_none_lines = cls.create_bom_lines(cls.bom_none, cls.raws, [3, 2, 1])

        cls.bom_lot = cls.env['mrp.bom'].create({
            'product_tmpl_id' : cls.produced_lot.product_tmpl_id.id,
            'product_uom_id' : cls.produced_lot.uom_id.id,
            'consumption' : 'flexible',
            'sequence' : 2
        })

        cls.bom_lot_lines = cls.create_bom_lines(cls.bom_lot, cls.raws, [3, 2, 1])

        cls.bom_serial = cls.env['mrp.bom'].create({
            'product_tmpl_id' : cls.produced_serial.product_tmpl_id.id,
            'product_uom_id' : cls.produced_serial.uom_id.id,
            'consumption' : 'flexible',
            'sequence' : 1
        })

        cls.bom_serial_lines = cls.create_bom_lines(cls.bom_serial, cls.raws, [3, 2, 1])

        #Manufacturing Orders
        cls.mo_none_tmpl = {
            'product_id' : cls.produced_none.id,
            'product_uom_id' : cls.produced_none.uom_id.id,
            'product_qty' : 1,
            'bom_id' : cls.bom_none.id
        }

        cls.mo_lot_tmpl = {
            'product_id' : cls.produced_lot.id,
            'product_uom_id' : cls.produced_lot.uom_id.id,
            'product_qty' : 1,
            'bom_id' : cls.bom_lot.id
        }

        cls.mo_serial_tmpl = {
            'product_id' : cls.produced_serial.id,
            'product_uom_id' : cls.produced_serial.uom_id.id,
            'product_qty' : 1,
            'bom_id' : cls.bom_serial.id
        }

    @classmethod
    def create_quant(cls, product, qty, offset=0, name="L"):
        i = 1
        if product.tracking == 'serial':
            i, qty = qty, 1
            if name == "L":
                name = "S"

        vals = []
        for x in range(1, i+1):
            qDict = {
                'location_id': cls.stock_id,
                'product_id': product.id,
                'inventory_quantity': qty,
            }

            if product.tracking != 'none':
                qDict['lot_id'] = cls.env['stock.lot'].create({
                    'name': name + str(offset + x),
                    'product_id': product.id,
                    'company_id': cls.env.company.id
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
                'product_id' : product.id,
                'product_qty' : quantities[seq],
                'product_uom_id' : product.uom_id.id,
                'sequence' : seq,
                'bom_id' : bom.id,
            })

        return cls.env['mrp.bom.line'].create(vals)

    @classmethod
    def create_mo(cls, template, count):
        vals = []
        for _ in range(count):
            vals.append(copy.deepcopy(template))
        return cls.env['mrp.production'].create(vals)

    def executeConsumptionTriggers(self, mrp_productions):
        """
        There's 3 different triggers to test : _onchange_producing(), action_generate_serial(), button_mark_done().

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
            mark_done_action = mrp_productions[i].button_mark_done()
            immediate_production_wizard = Form(
                self.env['mrp.immediate.production']
                .with_context(**mark_done_action['context'])
                ).save()
            error = False
            has_zero_tracked_component = not mrp_productions[i].picking_type_id.use_auto_consume_components_lots and \
                any(m.state not in ['done', 'cancel'] and m.has_tracking != 'none' and float_is_zero(m.quantity_done, m.product_uom.rounding) for m in mrp_productions[i].move_raw_ids)
            try:
                immediate_production_wizard.process()
            except UserError:
                error = True
            if has_zero_tracked_component:
                self.assertTrue(error, "Immediate Production Wizard shall raise an error.")
            else:
                self.assertFalse(error, "Immediate Production Wizard shall not raise an error.")
