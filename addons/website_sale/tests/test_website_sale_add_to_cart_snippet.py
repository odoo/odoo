# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import Command
from odoo.tests import HttpCase, tagged

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestAddToCartSnippet(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a dummy payment provider to ensure that the tour has at least one available to it.
        arch = """
        <form action="dummy" method="post">
            <input type="hidden" name="view_id" t-att-value="viewid"/>
            <input type="hidden" name="user_id" t-att-value="user_id.id"/>
        </form>
        """
        redirect_form = cls.env['ir.ui.view'].create({
            'name': "Dummy Redirect Form",
            'type': 'qweb',
            'arch': arch,
        })
        cls.dummy_provider = cls.env['payment.provider'].create({
            'name': "Dummy Provider",
            'code': 'none',
            'state': 'test',
            'is_published': True,
            'allow_tokenization': True,
            'redirect_form_view_id': redirect_form.id,
        })

    def test_configure_product(self):
        # Reset the company country id, which ensure that no country dependant fields are blocking the address form.
        self.env.company.country_id = self.env.ref('base.us')
        attribute = self.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({
                    'name': 'Red'
                }),
                Command.create({
                    'name': 'Pink'
                })
            ]
        })
        self.env['product.template'].create([{
            'name': 'Product No Variant',
            'website_published': True
        }, {
            'name': 'Product Yes Variant 1',
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids
                })
            ]
        }, {
            'name': 'Product Yes Variant 2',
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': attribute.value_ids
                })
            ]
        }])
        admin_partner = self.env.ref('base.user_admin').partner_id
        admin_partner.write({
            'street': "rue des Bourlottes, 9",
            'street2': "",
            'city': "Ramillies",
            'zip': 1367,
            'country_id': self.env.ref('base.be').id,
            'phone': "+32 123456789"
        })
        self.env.ref('base.user_admin').country_id = self.env.ref('base.be')
        self.start_tour("/", 'add_to_cart_snippet_tour', login="admin")
