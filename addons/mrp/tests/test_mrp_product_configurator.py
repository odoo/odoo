# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged
from odoo.addons.product.tests.test_configurator_common import TestProductConfiguratorCommon


@tagged('post_install', '-at_install')
class TestMrpProductConfiguratorUi(HttpCase, TestProductConfiguratorCommon):

    def test_01_mrp_product_configurator(self):
        grp_configurator = self.env.ref('mrp.group_mrp_configurator')
        self.env.user.write({'groups_id': [(4, grp_configurator.id)]})
        self.env['res.config.settings'].create({
            'group_mrp_configurator': True,
        }).execute()
        self.start_tour("/web", 'mrp_product_configurator_tour', step_delay=100, login="admin")
