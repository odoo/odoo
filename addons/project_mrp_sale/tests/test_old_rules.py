# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.fields import Command
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.addons.stock.tests.test_old_rules import TestStockOldRulesCommon


@tagged('post_install', '-at_install')
class TestProjectMrpSaleOldRules(TestStockOldRulesCommon, TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manufacture_route = cls.warehouse_3_steps.manufacture_pull_id.route_id
        cls.project = cls.env['project.project'].create({
            'name': 'SO Project',
        })

    def test_mo_get_project_from_so_in_3_steps_delivery(self):
        """ Ensure the project of MO is inherited from the SO in a 3-step delivery (Pick + Ship)."""
        self.product_4.route_ids = [Command.set([self.manufacture_route.id, self.mto_route.id])]

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'project_id': self.project.id,
            'order_line': [Command.create({
                'product_id': self.product_4.id,
                'product_uom_qty': 1,
                'price_unit': 100,
            })],
            'warehouse_id': self.warehouse_3_steps.id,
        })

        sale_order.action_confirm()

        mo = sale_order.mrp_production_ids

        self.assertTrue(mo)
        self.assertEqual(mo.project_id, self.project)
