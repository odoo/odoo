# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.point_of_sale.tests.common import CommonPosTest


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestPosStock(CommonPosTest):

    @classmethod
    def _setup_pos_configs(cls):
        # Existing POS configurations would prevent archiving their warehouse.
        pass

    def test_pos_config_creates_warehouse(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        if warehouse:
            warehouse.write({'active': False, 'name': 'Archived ' + warehouse[0].name})
        pos_config = self.env['pos.config'].create({
            'name': 'Shop',
            'module_pos_restaurant': False,
        })
        self.assertEqual(pos_config.warehouse_id.code, 'Sho')
