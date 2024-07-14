# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestBarcodeClientAction(HttpCase):
    def setUp(self):
        super(TestBarcodeClientAction, self).setUp()
        # Disables the sound effect so we don't go crazy while running the test tours locally.
        self.env['ir.config_parameter'].set_param('stock_barcode.mute_sound_notifications', True)

        self.uid = self.env.ref('base.user_admin').id
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.stock_location.write({
            'barcode': 'LOC-01-00-00',
        })
        self.customer_location = self.env.ref('stock.stock_location_customers')
        self.pack_location = self.env.ref('stock.location_pack_zone')
        self.shelf3 = self.env['stock.location'].create({
            'name': 'Section 3',
            'location_id': self.stock_location.id,
            'barcode': 'shelf3',
        })
        self.shelf1 = self.env["stock.location"].create({
            'name': 'Section 1',
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
            'barcode': 'LOC-01-01-00',
        })
        self.shelf2 = self.env['stock.location'].create({
            'name': 'Section 2',
            'location_id': self.env.ref('stock.warehouse0').lot_stock_id.id,
            'barcode': 'LOC-01-02-00',
        })
        self.shelf4 = self.env['stock.location'].create({
            'name': 'Section 4',
            'location_id': self.stock_location.id,
            'barcode': 'shelf4',
        })
        self.picking_type_in = self.env.ref('stock.picking_type_in')
        self.picking_type_internal = self.env.ref('stock.picking_type_internal')
        self.picking_type_out = self.env.ref('stock.picking_type_out')

        self.uom_unit = self.env.ref('uom.product_uom_unit')
        self.uom_dozen = self.env.ref('uom.product_uom_dozen')

        # Two stockable products without tracking
        self.product1 = self.env['product.product'].create({
            'name': 'product1',
            'default_code': 'TEST',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product1',
        })
        self.product2 = self.env['product.product'].create({
            'name': 'product2',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'product2',
        })
        self.productserial1 = self.env['product.product'].create({
            'name': 'productserial1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productserial1',
            'tracking': 'serial',
        })
        self.productlot1 = self.env['product.product'].create({
            'name': 'productlot1',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': 'productlot1',
            'tracking': 'lot',
        })
        self.package = self.env['stock.quant.package'].create({
            'name': 'P00001',
        })
        self.owner = self.env['res.partner'].create({
            'name': 'Azure Interior',
        })

        # Creates records specific to GS1 use cases.
        self.product_tln_gtn8 = self.env['product.product'].create({
            'name': 'Battle Droid',
            'default_code': 'B1',
            'type': 'product',
            'tracking': 'lot',
            'categ_id': self.env.ref('product.product_category_all').id,
            'barcode': '76543210',  # (01)00000076543210 (GTIN-8 format)
            'uom_id': self.env.ref('uom.product_uom_unit').id
        })

        self.call_count = 0

    def clean_access_rights(self):
        """ Removes all access right link to stock application to the users
        given as parameter"""
        grp_lot = self.env.ref('stock.group_production_lot')
        grp_multi_loc = self.env.ref('stock.group_stock_multi_locations')
        grp_pack = self.env.ref('stock.group_tracking_lot')
        grp_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(3, grp_lot.id)]})
        self.env.user.write({'groups_id': [(3, grp_multi_loc.id)]})
        self.env.user.write({'groups_id': [(3, grp_pack.id)]})
        # Explicitly remove the UoM group.
        group_user = self.env.ref('base.group_user')
        group_user.write({'implied_ids': [(3, grp_uom.id)]})
        self.env.user.write({'groups_id': [(3, grp_uom.id)]})

    def tearDown(self):
        self.call_count = 0
        super(TestBarcodeClientAction, self).tearDown()

    def _get_client_action_url(self, picking_id):
        action = self.env["ir.actions.actions"]._for_xml_id("stock_barcode.stock_barcode_picking_client_action")
        return '/web#action=%s&active_id=%s' % (action['id'], picking_id)
