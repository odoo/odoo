from odoo import Command
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger


@tagged('-at_install', 'post_install')
class TestPackagingTours(HttpCase):

    def _get_product_url(self, product_id):
        return '/odoo/action-stock.product_template_action_product/%s' % (product_id)

    def test_barcode_duplication_error(self):
        """ Test the barcode duplication error when creating a new product with an existing barcode """
        product_a = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'tracking': 'none',
            'uom_id': self.env.ref('uom.product_uom_unit').id,
            'uom_ids': [Command.link(self.env.ref('uom.product_uom_pack_6').id)],
            'product_uom_ids': [Command.create({
                'barcode': 'test-1234',
                'uom_id': self.env.ref('uom.product_uom_pack_6').id,
            })]
        })
        url = self._get_product_url(product_a.product_tmpl_id.id)
        self.env['res.config.settings'].create({
            'group_uom': True,
        }).execute()
        with mute_logger('odoo.sql_db', 'odoo.http'):
            self.start_tour(url, 'test_barcode_duplication_error', login='admin', timeout=60)
