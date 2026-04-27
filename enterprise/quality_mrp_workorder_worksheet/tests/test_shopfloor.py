# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command

from odoo.tests import Form
from odoo.tests.common import tagged
from odoo.addons.quality_control_worksheet.tests.test_quality_worksheet import TestQualityWorksheet
from odoo.addons.mrp_workorder.tests.test_shopfloor import TestShopFloor

@tagged('post_install', '-at_install')
class TestShopFloorWorksheet(TestShopFloor, TestQualityWorksheet):
    def test_worksheet_quality_check(self):
        self.env.ref("base.user_admin").groups_id += self.env.ref('mrp.group_mrp_routings')
        warehouse = self.env.ref("stock.warehouse0")
        final_product, component = self.env['product.product'].create([
            {
                'name': 'Lovely Product',
                'is_storable': True,
                'tracking': 'none',
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
                'product_ids': [Command.link(final_product.id)],
                'operation_id': bom.operation_ids.id,
                'title': 'Lovely Worksheet',
                'product_ids': final_product.ids,
                'test_type_id': self.ref('quality_control_worksheet.test_type_worksheet'),
                'worksheet_template_id':  self.worksheet_template.id,
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
        self.start_tour('/odoo/shop-floor', "test_worksheet_quality_check", login='admin')
        self.assertEqual(mo.workorder_ids.state, "done")
