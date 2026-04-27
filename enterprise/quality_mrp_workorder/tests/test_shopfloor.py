# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command

from odoo.tests import Form
from odoo.tests.common import tagged
from odoo.addons.quality_control.tests.test_common import TestQualityCommon
from odoo.addons.mrp_workorder.tests.test_shopfloor import TestShopFloor

@tagged('post_install', '-at_install')
class TestShopFloorQuality(TestShopFloor, TestQualityCommon):

    def test_shop_floor_spreadsheet(self):
        self.env.ref('base.group_user').implied_ids += (
            self.env.ref('mrp.group_mrp_routings')
        )
        snow_leopard = self.env['product.product'].create({
            'name': 'Snow leopard',
            'is_storable': True,
        })
        mountains = self.env['mrp.workcenter'].create({
            'name': 'Mountains',
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        leg = self.env['product.product'].create({
            'name': 'Leg',
            'is_storable': True,
        })
        warehouse = self.env['stock.warehouse'].search([], limit=1)
        stock_location = warehouse.lot_stock_id
        self.env['stock.quant']._update_available_quantity(leg, stock_location, quantity=100)
        bom = self.env['mrp.bom'].create({
            'product_id': snow_leopard.id,
            'product_tmpl_id': snow_leopard.product_tmpl_id.id,
            'product_uom_id': snow_leopard.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'operation_ids': [
                (0, 0, {
                'name': 'op1',
                'workcenter_id': mountains.id,
            })],
            'bom_line_ids': [
                (0, 0, {'product_id': leg.id, 'product_qty': 4}),
            ]
        })
        picking_type = warehouse.manu_type_id
        spreadsheet = self.env['quality.spreadsheet.template'].create({
            'check_cell': 'A1',
            'name': 'my spreadsheet quality check template',
        })
        self.env['quality.point'].create([
            {
                'picking_type_ids': [(4, picking_type.id)],
                'product_ids': [(4, snow_leopard.id)],
                'operation_id': bom.operation_ids[0].id,
                'title': 'My spreadsheet check',
                'test_type_id': self.env.ref('quality_control.test_type_spreadsheet').id,
                'sequence': 0,
                'spreadsheet_template_id': spreadsheet.id,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': snow_leopard.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        action = self.env['ir.actions.actions']._for_xml_id('mrp_workorder.action_mrp_display')
        url = f"/odoo/action-{action['id']}"
        self.start_tour(url, 'test_shop_floor_spreadsheet', login='admin')
        self.assertRecordValues(mo.workorder_ids[0].check_ids, [
            {'quality_state': 'fail'},
        ])

    def test_register_sn_production_quality_check(self):
        warehouse = self.env.ref("stock.warehouse0")
        final_product, component = self.env['product.product'].create([
            {
                'name': 'Lovely Product',
                'is_storable': True,
                'tracking': 'serial',
            },
            {
                'name': 'Lovely Component',
                'is_storable': True,
                'tracking': 'none',
            },
        ])
        self.env['stock.quant']._update_available_quantity(component, warehouse.lot_stock_id, quantity=10)
        workcenter = self.env['mrp.workcenter'].create({
            'name': 'Lovely Workcenter',
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({'name': 'Lovely Operation', 'workcenter_id': workcenter.id}),
            ],
            'bom_line_ids': [
                Command.create({'product_id': component.id, 'product_qty': 1.0}),
            ]
        })
        self.env['quality.point'].create([
            {
                'picking_type_ids': [Command.link(warehouse.manu_type_id.id)],
                'operation_id': bom.operation_ids.id,
                'title': 'Lovely Production Registering',
                'test_type_id': self.ref('mrp_workorder.test_type_register_production'),
                'sequence': 1,
            },
        ])
        mo = self.env['mrp.production'].create({
            'product_id': final_product.id,
            'product_qty': 1,
            'bom_id': bom.id,
        })
        mo.action_confirm()
        mo.action_assign()
        self.assertEqual(mo.reservation_state, 'assigned')
        mo.button_plan()
        action = mo.workorder_ids.action_open_mes()
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, "test_register_sn_production_quality_check", login='admin')
        self.assertRecordValues(mo.lot_producing_id, [{'name': 'SN0012'}])
