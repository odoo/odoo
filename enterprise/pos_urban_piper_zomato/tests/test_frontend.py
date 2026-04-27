# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.point_of_sale.tests.common import archive_products
from odoo.addons.pos_urban_piper.models.pos_urban_piper_request import UrbanPiperClient
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestTaxCommonPOS
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestPosUrbanPiperZomatoCommon(TestTaxCommonPOS):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('in')
    def setUpClass(cls):
        super().setUpClass()
        archive_products(cls.env)
        cls.urban_piper_config = cls.env['pos.config'].create({
            'name': 'Urban Piper',
            'module_pos_urban_piper': True,
            'urbanpiper_delivery_provider_ids': [Command.set([cls.env.ref('pos_urban_piper_zomato.pos_delivery_provider_zomato').id])],
            'urbanpiper_webhook_url': cls.env['pos.config'].get_base_url()
        })
        cls.product_tag_1 = cls.env['product.tag'].create({
            'name': 'allergen-milk',
        })
        cls.product_1 = cls.env['product.template'].create({
            'name': 'Product 1',
            'available_in_pos': True,
            'taxes_id': [Command.set([cls.env['account.chart.template'].ref("sgst_sale_5").id])],
            'product_tag_ids': [cls.product_tag_1.id],
            'type': 'consu',
            'list_price': 100.0,
        })
        cls.product_2 = cls.env['product.template'].create({
            'name': 'Product 2',
            'available_in_pos': True,
            'taxes_id': [Command.set([cls.env['account.chart.template'].ref("sgst_sale_18").id])],
            'type': 'consu',
            'list_price': 200.0,
        })

    def test_zomato_tags_included_in_urban_piper_items(self):
        """
        Test that product tags are correctly sent to Urban Piper.
        """
        up = UrbanPiperClient(self.urban_piper_config)
        items = up._prepare_items_data([self.product_1, self.product_2])
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['tags'].get('zomato', []), ['alcohol-absent', 'allergen-milk'])
        self.assertEqual(
            items[1]['tags'].get('default', []),
            ['packaged-good']
        )
