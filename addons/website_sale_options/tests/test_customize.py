# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_admin_shop_customize_tour(self):
        self.env.ref('product.group_product_variant').write({
            'users': [(4, self.env.ref('base.user_admin').id)]
        })

        self.phantom_js("/", "odoo.__DEBUG__.services['web_tour.tour'].run('shop_customize')", "odoo.__DEBUG__.services['web_tour.tour'].tours.shop_customize.ready", login="admin")
