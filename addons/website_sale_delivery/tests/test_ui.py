# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_free_delivery_when_exceed_threshold(self):
        
        # Avoid Shipping/Billing address page
        self.env.ref('base.partner_admin').write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })

        office_chair = self.env['product.product'].create({
            'name': 'Office Chair Black TEST',
            'list_price': 12.50,
        })
        self.env.ref("delivery.free_delivery_carrier").write({
            'name': 'Delivery Now Free Over 10',
            'fixed_price': 2,
            'free_over': True,
            'amount': 10,
        })
        self.product_delivery_poste = self.env['product.product'].create({
            'name': 'The Poste',
            'type': 'service',
            'categ_id': self.env.ref('delivery.product_category_deliveries').id,
            'sale_ok': False,
            'purchase_ok': False,
            'list_price': 20.0,
        })
        self.carrier = self.env['delivery.carrier'].create({
            'name': 'The Poste',
            'sequence': 9999, # ensure last to load price async
            'fixed_price': 20.0,
            'delivery_type': 'base_on_rule',
            'product_id': self.product_delivery_poste.id,
            'website_published': True,
        })
        self.env['delivery.price.rule'].create([{
            'carrier_id': self.carrier.id,
            'max_value': 5,
            'list_base_price': 20,
        }, {
            'carrier_id': self.carrier.id,
            'operator': '>=',
            'max_value': 5,
            'list_base_price': 50,
        }, {
            'carrier_id': self.carrier.id,
            'operator': '>=',
            'max_value': 300,
            'variable': 'price',
            'list_base_price': 0,
        }])

        self.env['account.journal'].create({'name': 'Cash - Test', 'type': 'cash', 'code': 'CASH - Test'})

        # Ensure "Wire Transfer" is the default provider.
        # Providers are sorted by state, showing `test` providers first (don't ask why).
        self.env.ref("payment.payment_provider_transfer").write({"state": "test"})

        self.start_tour("/", 'check_free_delivery', login="admin")
