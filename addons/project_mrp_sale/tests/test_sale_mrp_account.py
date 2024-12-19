# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_mrp.tests.test_multistep_manufacturing import TestMultistepManufacturing
from odoo.tests import common


@common.tagged('post_install', '-at_install')
class TestSaleMrpAccount(TestMultistepManufacturing):
    def test_mo_get_project_from_so(self):
        """ Ensure the project of MO is inherited from the SO if no project is set """
        self.user_stock_manager.sudo().groups_id += self.env.ref('project.group_project_manager')
        project = self.env['project.project'].create({
            'name': 'SO Project',
        })
        self.sale_order.project_id = project
        self.assertFalse(self.sale_order.mrp_production_ids.project_id)
        self.sale_order.action_confirm()
        self.assertEqual(self.sale_order.mrp_production_ids.project_id, project)
