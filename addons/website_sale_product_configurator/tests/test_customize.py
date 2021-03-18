# Part of Odoo. See LICENSE file for full copyright and licensing details.

<<<<<<< HEAD
from odoo.tests.common import HttpSavepointCase
=======
from odoo.tests.common import HttpCase
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729
from odoo.addons.sale_product_configurator.tests.common import TestProductConfiguratorCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
<<<<<<< HEAD
class TestUi(HttpSavepointCase, TestProductConfiguratorCommon):
=======
class TestUi(HttpCase, TestProductConfiguratorCommon):
>>>>>>> 3f1a31c4986257cd313d11b42d8a60061deae729

    def test_01_admin_shop_custom_attribute_value_tour(self):
        # fix runbot, sometimes one pricelist is chosen, sometimes the other...
        pricelists = self.env['website'].get_current_website().get_current_pricelist() | self.env.ref('product.list0')
        self._create_pricelist(pricelists)
        self.start_tour("/", 'a_shop_custom_attribute_value', login="admin")
