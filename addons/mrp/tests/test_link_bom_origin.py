from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestLinkBomOpenOrigin(TransactionCase):

    def test_plm_revision_merges_component_delta_into_open_pick(self):
        """Revise the BoM through PLM, then Update BoM must absorb the delta.

        Same-line Update BoM keeps the bom line record, so the pick still merges.
        A PLM revision creates new bom lines. With a phantom kit on the MO the
        merge key includes bom_line_id, and the decrease must still land on the
        open pick instead of a Pre-Production -> Stock return.
        """
        # mrp.bom.version is added by mrp_plm. Without that module there is no
        # new BoM revision to apply, and this case cannot be built.
        if 'version' not in self.env['mrp.bom']._fields:
            self.skipTest('mrp_plm is not installed')

        warehouse = self.env['stock.warehouse'].create({
            'name': 'Link BoM WH',
            'code': 'LBW',
        })
        warehouse.manufacture_steps = 'pbm'
        uom = self.env.ref('uom.product_uom_unit')
        finished, component, kit_part = self.env['product.product'].create([{
            'name': 'Finished',
            'type': 'product',
            'uom_id': uom.id,
            'uom_po_id': uom.id,
            'route_ids': [(6, 0, [
                warehouse.manufacture_pull_id.route_id.id,
                warehouse.mto_pull_id.route_id.id,
            ])],
        }, {
            'name': 'Component',
            'type': 'product',
            'uom_id': uom.id,
            'uom_po_id': uom.id,
        }, {
            'name': 'Kit part',
            'type': 'consu',
            'uom_id': uom.id,
            'uom_po_id': uom.id,
        }])
        kit = self.env['product.product'].create({
            'name': 'Kit',
            'type': 'consu',
            'uom_id': uom.id,
            'uom_po_id': uom.id,
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'product_uom_id': uom.id,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {
                'product_id': kit_part.id,
                'product_qty': 1.0,
                'product_uom_id': uom.id,
            })],
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_id': finished.id,
            'product_qty': 1.0,
            'product_uom_id': uom.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': component.id, 'product_qty': 4.0, 'product_uom_id': uom.id}),
                (0, 0, {'product_id': kit.id, 'product_qty': 1.0, 'product_uom_id': uom.id}),
            ],
        })
        production = self.env['mrp.production'].create({
            'product_id': finished.id,
            'product_qty': 10.0,
            'product_uom_id': uom.id,
            'bom_id': bom.id,
            'picking_type_id': warehouse.manu_type_id.id,
            'location_src_id': warehouse.pbm_loc_id.id,
            'location_dest_id': warehouse.lot_stock_id.id,
        })
        production.action_confirm()

        raw = production.move_raw_ids.filtered(lambda move: move.product_id == component)
        pick = raw.move_orig_ids
        self.assertEqual(raw.product_uom_qty, 40.0)
        self.assertEqual(len(pick), 1)
        self.assertEqual(pick.product_uom_qty, 40.0)

        new_bom = bom.copy()
        new_line = new_bom.bom_line_ids.filtered(lambda line: line.product_id == component)
        new_line.product_qty = 3.0
        new_bom.write({
            'version': bom.version + 1,
            'previous_bom_id': bom.id,
        })
        new_bom.apply_new_version()
        production.invalidate_recordset()
        self.assertEqual(production.latest_bom_id, new_bom)

        production.action_update_bom()

        raw = production.move_raw_ids.filtered(lambda move: move.product_id == component)
        pick = raw.move_orig_ids.filtered(lambda move: move.state not in ('done', 'cancel'))
        self.assertEqual(raw.product_uom_qty, 30.0)
        self.assertEqual(pick.product_uom_qty, 30.0)
        self.assertEqual(pick.bom_line_id, new_line)
        reverse_moves = self.env['stock.move'].search([
            ('product_id', '=', component.id),
            ('location_id', '=', warehouse.pbm_loc_id.id),
            ('location_dest_id', '=', warehouse.lot_stock_id.id),
            ('state', '!=', 'cancel'),
        ])
        self.assertFalse(reverse_moves)
