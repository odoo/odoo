# -*- coding: utf-8 -*-
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.tests import tagged, HttpCase

@tagged('post_install', '-at_install')
class TestDelivery(HttpCase):
    def test_address_states(self):
        US = self.env.ref('base.us')
        MX = self.env.ref('base.mx')

        # Set all carriers to mexico
        self.env['delivery.carrier'].sudo().search([('website_published', '=', True)]).country_ids = [(6, 0, [MX.id])]

        # Create a new carrier to only one state in mexico
        self.env['delivery.carrier'].create({
                'name': "One_state",
                'product_id': self.env['product.product'].create({'name': "delivery product"}).id,
                'website_published': True,
                'country_ids': [(6, 0, [MX.id])],
                'state_ids': [(6, 0, [MX.state_ids.ids[0]])]
        })

        country_info = WebsiteSale().country_infos(country=MX, mode="shipping")
        self.assertEqual(len(country_info['states']), len(MX.state_ids))

        country_info = WebsiteSale().country_infos(country=US, mode="shipping")
        self.assertEqual(len(country_info['states']), 0)
