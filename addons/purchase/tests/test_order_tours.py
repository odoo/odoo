# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestPurchaseOrderTour(HttpCase):

    def test_purchase_order_vendor_conformation(self):
        """ Computation of the unit price if it is manually set and also change it with respect to vendor  """
        self.env['res.config.settings'].create({'group_uom': True}).execute()

        vendor1 = self.env['res.partner'].create({
            'name': 'Vendor1'
        })
        self.env['res.partner'].create({
            'name': 'Vendor2'
        })
        self.env['product.product'].create({
            'name': 'Super Product',
            'standard_price': 60.0,
            'list_price': 90.0,
            'type': 'consu',
            'seller_ids': [(0, 0, {
                'partner_id': vendor1.id,
                'min_qty': 1.0,
                'price': 50.0,
            })]
        })

        action = self.env["ir.actions.actions"]._for_xml_id("purchase.purchase_rfq")
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, 'purchase_order_vendor_conformation_tour', login='admin', timeout=180)
