# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged
from odoo.addons.product.tests.common import ProductVariantsCommon
from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestProductConfiguratorData(HttpCase, ProductVariantsCommon, SaleCommon):

    def test_dropped_attribute_isnt_shown(self):
        self.assertEqual(len(self.product_template_sofa.product_variant_ids), 3)
        self.empty_order.order_line = [
            Command.create({
                'product_id': product.id
            })
            for product in self.product_template_sofa.product_variant_ids
        ]
        self.empty_order.action_confirm()

        self.product_template_sofa.attribute_line_ids.value_ids -= self.color_attribute_red
        self.assertEqual(len(self.product_template_sofa.product_variant_ids.filtered('active')), 2)

        self.authenticate('demo', 'demo')
        base_url = self.product_template_sofa.get_base_url()
        response = self.opener.post(
            url=base_url + '/sale_product_configurator/get_values',
            json={
                'params': dict(
                    product_template_id=self.product_template_sofa.id,
                    quantity=1.0,
                    currency_id=1,
                    so_date=str(self.env.cr.now()),
                    product_uom_id=None,
                    company_id=None,
                    pricelist_id=None,
                    ptav_ids=None,
                    only_main_product=False,
                ),
            }
        )
        result = response.json()['result']

        # Make sure the inactive ptav was removed from the loaded attributes
        self.assertEqual(len(result['products'][0]['attribute_lines'][0]['attribute_values']), 2)
