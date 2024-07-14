# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, tagged
from odoo.addons.stock_barcode.tests.test_barcode_client_action import TestBarcodeClientAction


@tagged('post_install', '-at_install')
class TestMRPBarcodeClientAction(TestBarcodeClientAction):
    def setUp(self):
        super().setUp()

        self.component01 = self.env['product.product'].create({
            'name': 'Compo 01',
            'type': 'product',
            'barcode': 'compo01',
        })
        self.component_lot = self.env['product.product'].create({
            'name': 'Compo Lot',
            'type': 'product',
            'barcode': 'compo_lot',
            'tracking': 'lot',
        })

        self.final_product = self.env['product.product'].create({
            'name': 'Final Product',
            'type': 'product',
            'barcode': 'final',
        })

        self.final_product_lot = self.env['product.product'].create({
            'name': 'Final Product2',
            'type': 'product',
            'barcode': 'final_lot',
            'tracking': 'lot',
        })

        self.by_product = self.env['product.product'].create({
            'name': 'By Product',
            'type': 'product',
            'barcode': 'byproduct'
        })

        self.bom_lot = self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product_lot.product_tmpl_id.id,
            'product_qty': 2.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
                (0, 0, {'product_id': self.component_lot.id, 'product_qty': 2.0}),
            ],
        })

    def test_barcode_production_process(self):
        """Create a manufacturing order in the backend and process it
            in the barcode app.
        """
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })

        mo = self.env['mrp.production'].create({
            'product_id': self.final_product.id,
            'product_qty': 1,
            'move_raw_ids': [(0, 0, {
                'product_id': self.component01.id,
                'product_uom_qty': 2
            })]
        })

        mo.action_confirm()

        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_process_confirmed_mo', login='admin', timeout=180)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 1)
        self.assertEqual(mo.qty_producing, 1)

    def test_barcode_production_create(self):
        """Create a manufacturing order from barcode app
        """
        self.clean_access_rights()
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_create', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 2)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 2},
        ])

    def test_barcode_production_create_bom(self):
        """ Creates a manufacturing order and scans a product who has a BoM, it
        should create a line for each component, and automatically increase
        their quantity every time the final product is scanned.
        """
        self.clean_access_rights()
        # Creates a BoM.
        component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'type': 'product',
            'barcode': 'compo02',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
                (0, 0, {'product_id': component02.id, 'product_qty': 3.0}),
            ],
        })
        # Adds some quantities in stock for the components.
        for component in [self.component01, component02]:
            self.env['stock.quant'].create({
                'quantity': 99,
                'product_id': component.id,
                'location_id': self.stock_location.id,
            })

        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_create_bom', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 3)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 2, 'quantity': 6},
            {'product_id': component02.id, 'product_uom_qty': 3, 'quantity': 9},
        ])

    def test_barcode_production_create_tracked_bom(self):
        """Create a manufacturing order with bom from barcode app, with byproducts
        """
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_by_product = self.env.ref('mrp.group_mrp_byproducts')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0), (4, grp_by_product.id, 0)]})
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        lot_id = self.env['stock.lot'].create({
            'name': 'lot01',
            'product_id': self.component_lot.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_id.id
        })
        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_create_tracked_bom', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.state, 'done')
        self.assertEqual(mo.qty_produced, 3)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 3, 'quantity': 3},
            {'product_id': self.component_lot.id, 'product_uom_qty': 3, 'quantity': 3},
        ])
        self.assertRecordValues(mo.move_byproduct_ids, [
            {'product_id': self.by_product.id, 'product_uom_qty': 2, 'quantity': 2},
        ])

    def test_barcode_production_reserved_from_multiple_locations(self):
        """ Process a production with components reserved in different locations
        and with the scan of the source for each component.
        """
        self.clean_access_rights()
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_multi_loc.id, 0)]})
        picking_type_production = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'), ('company_id', '=', self.env.company.id)])
        picking_type_production.restrict_scan_dest_location = 'no'
        picking_type_production.restrict_scan_source_location = 'mandatory'
        # Creates a BoM and adds some quantities for the components in different locations.
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
            ],
        })
        self.env['stock.quant'].create({
            'quantity': 1,
            'product_id': self.component01.id,
            'location_id': self.shelf1.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.shelf2.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.shelf3.id,
        })
        self.env['stock.quant'].create({
            'quantity': 1,
            'product_id': self.component01.id,
            'location_id': self.shelf4.id,
        })
        # Prepares a production for 3x final product, then process it in the Barcode App.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.final_product
        mo_form.product_qty = 3
        mo = mo_form.save()
        mo.action_confirm()

        action = self.env.ref('stock_barcode_mrp.stock_barcode_mo_client_action')
        url = '/web?debug=assets#action=%s&active_id=%s' % (action.id, mo.id)
        self.start_tour(url, 'test_barcode_production_reserved_from_multiple_locations', login='admin', timeout=180)

    def test_barcode_production_scan_other_than_reserved(self):
        """ Process a production with a reserved untracked component and a lot tracked component.
        Scan a different lot than the reserved lot and scan a different (location) component than
        the reserved location."""
        self.clean_access_rights()
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        self.env.user.write({'groups_id': [(4, grp_lot.id, 0), (4, grp_multi_loc.id, 0)]})
        picking_type_production = self.env['stock.picking.type'].search([
            ('code', '=', 'mrp_operation'), ('company_id', '=', self.env.company.id)])
        picking_type_production.restrict_scan_source_location = 'mandatory'
        # Prepares a production for 2x final product, then process it in the Barcode App.
        lot_01 = self.env['stock.lot'].create({
            'name': 'lot_01',
            'product_id': self.component_lot.id,
            'company_id': self.env.company.id,
        })
        lot_02 = self.env['stock.lot'].create({
            'name': 'lot_02',
            'product_id': self.component_lot.id,
            'company_id': self.env.company.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component01.id,
            'location_id': self.shelf1.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_01.id
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.component_lot.id,
            'location_id': self.stock_location.id,
            'lot_id': lot_02.id
        })

        untracked_product_bom_line = self.bom_lot.bom_line_ids.filtered(lambda l: l.product_id == self.component01)
        untracked_product_bom_line.manual_consumption = True

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.final_product_lot
        mo_form.product_qty = 2
        mo = mo_form.save()
        mo.action_confirm()

        action = self.env.ref('stock_barcode_mrp.stock_barcode_mo_client_action')
        url = '/web?debug=assets#action=%s&active_id=%s' % (action.id, mo.id)
        self.start_tour(url, 'test_barcode_production_scan_other_than_reserved', login='admin', timeout=180)

        # Checks move lines values after MO is completed.
        self.assertEqual(mo.state, "done")
        # ensure that lot ml not scanned by validation time is removed
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 2)
        self.assertRecordValues(mo.move_raw_ids, [
            {'product_id': self.component01.id, 'product_uom_qty': 2, 'quantity': 2, 'location_id': self.stock_location.id},
            {'product_id': self.component_lot.id, 'product_uom_qty': 2, 'quantity': 2, 'lot_ids': lot_02, 'location_id': self.stock_location.id},
        ])
        self.assertRecordValues(mo.move_raw_ids.move_line_ids, [
            {'product_id': self.component01.id, 'quantity': 2, 'location_id': self.shelf1.id},
            {'product_id': self.component_lot.id, 'quantity': 2, 'lot_id': lot_02, 'location_id': self.stock_location.id},
        ])
        self.assertRecordValues(mo.finished_move_line_ids, [
            {'product_id': self.final_product_lot.id, 'quantity': 2},
        ])
        self.assertEqual(mo.finished_move_line_ids.lot_id.name, "finished_lot")

    def test_barcode_production_component_no_stock(self):
        """Create MO from barcode for final product with bom but component has not stock
        """
        self.clean_access_rights()
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 2.0}),
            ],
        })
        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_component_no_stock', login='admin', timeout=180)

    def test_barcode_production_components_reservation_state(self):
        """ When components are unreserved, they should not be visible in the
        Barcode app nor re-reserved when the MO is opened.
        Only reserved components should be visible in the barcode."""
        self.clean_access_rights()
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.component01.id,
            'location_id': self.stock_location.id,
        })
        mo = self.env['mrp.production'].create({
            'product_id': self.final_product.id,
            'product_qty': 1,
            'move_raw_ids': [(0, 0, {
                'product_id': self.component01.id,
                'product_uom_qty': 2,
                'picked': False,
            })]
        })
        mo.action_confirm()
        action = self.env.ref('stock_barcode_mrp.stock_barcode_mo_client_action')
        url = f"/web#action={action.id}&active_id={mo.id}"

        # when MO component's are reserved
        self.assertEqual(mo.move_raw_ids.move_line_ids.quantity, mo.move_raw_ids.product_uom_qty)
        self.start_tour(url, 'test_barcode_production_components_reservation_state_reserved', login='admin', timeout=180)

        # when MO component's are unreserved
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 1)
        mo.do_unreserve()
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 0)
        self.start_tour(url, 'test_barcode_production_components_reservation_state_unreserved', login='admin', timeout=180)
        self.assertEqual(
            len(mo.move_raw_ids.move_line_ids), 0,
            "Verify MO components are still unreserved after open the MO in the Barcode app")

    def test_barcode_production_add_scrap(self):
        """ Process a production where one of the component is scraped
        """
        self.clean_access_rights()
        # Creates a BoM.
        component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'type': 'product',
            'barcode': 'compo02',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': component02.id, 'product_qty': 1.0}),
            ],
        })
        # Adds some quantities in stock for the components.
        for component in [self.component01, component02]:
            self.env['stock.quant'].create({
                'quantity': 99,
                'product_id': component.id,
                'location_id': self.stock_location.id,
            })

        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_add_scrap', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(mo.scrap_count, 1)
        self.assertEqual(mo.scrap_ids.product_id.name, 'Compo 01')

    def test_barcode_production_add_byproduct(self):
        """ Process a production where we add a byproduct.
        We ensure the final product can't be added as a byproduct.
        """
        self.clean_access_rights()
        grp_by_product = self.env.ref('mrp.group_mrp_byproducts')
        self.env.user.write({'groups_id': [(4, grp_by_product.id, 0)]})
        # Creates a BoM.
        component02 = self.env['product.product'].create({
            'name': 'Compo 02',
            'type': 'product',
            'barcode': 'compo02',
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': component02.id, 'product_qty': 1.0}),
            ],
        })
        # Adds some quantities in stock for the components.
        for component in [self.component01, component02]:
            self.env['stock.quant'].create({
                'quantity': 99,
                'product_id': component.id,
                'location_id': self.stock_location.id,
            })

        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_add_byproduct', login='admin', timeout=180)
        mo = self.env['mrp.production'].search([], order='id desc', limit=1)
        self.assertEqual(len(mo.move_byproduct_ids), 1)
        self.assertEqual(mo.move_byproduct_ids.product_id.display_name, 'By Product')

    def test_split_line_on_exit_for_production(self):
        """ Ensures that exit an unfinished MO will split the uncompleted move lines to have one
        move line with all picked quantity and one move line with the remaining qty."""
        self.clean_access_rights()

        # Creates a product with a BoM.
        product_final = self.env['product.product'].create({
            'name': 'Final Product',
            'type': 'product',
        })
        bom = self.env['mrp.bom'].create({
            'product_id': product_final.id,
            'product_tmpl_id': product_final.product_tmpl_id.id,
            'product_uom_id': product_final.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption':  'flexible',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product1.id, 'product_qty': 2}),
                (0, 0, {'product_id': self.product2.id, 'product_qty': 1})
            ]})

        # Adds some quantity in stock.
        self.env['stock.quant'].create({
            'quantity': 4,
            'product_id': self.product1.id,
            'location_id': self.stock_location.id,
        })
        self.env['stock.quant'].create({
            'quantity': 2,
            'product_id': self.product2.id,
            'location_id': self.stock_location.id,
        })

        # Creates and confirms manufacturing order for 2 product_final.
        production = self.env['mrp.production'].create({
            'name': "production_split_line_on_exit",
            'bom_id': bom.id,
            'product_id': product_final.id,
            'product_qty': 2,
        })
        production.action_confirm()

        action_id = self.env.ref('stock_barcode.stock_barcode_action_main_menu')
        url = f"/web#action={action_id.id}"
        self.start_tour(url, 'test_split_line_on_exit_for_production', login='admin')
        # Checks production moves raw values.
        self.assertRecordValues(production.move_raw_ids, [
            {'product_id': self.product1.id, 'quantity': 3, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 1, 'picked': True},
            {'product_id': self.product2.id, 'quantity': 1, 'picked': False},
            {'product_id': self.product1.id, 'quantity': 1, 'picked': False},
        ])

    def test_barcode_production_component_different_uom(self):
        self.clean_access_rights()
        self.env.ref('base.user_admin').groups_id += self.env.ref('uom.group_uom')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        uom_gm = self.env.ref('uom.product_uom_gram')
        self.component01.uom_id = uom_gm
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                (0, 0, {'product_id': self.component01.id, 'product_qty': 1.0, 'product_uom_id': uom_kg.id}),
            ],
        })
        action_id = self.env.ref('stock_barcode.stock_picking_type_action_kanban')
        url = "/web#action=" + str(action_id.id)
        self.start_tour(url, 'test_barcode_production_component_different_uom', login='admin', timeout=180)
