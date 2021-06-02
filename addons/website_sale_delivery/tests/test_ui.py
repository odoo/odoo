import odoo.tests
# Part of Odoo. See LICENSE file for full copyright and licensing details.


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_free_delivery_when_exceed_threshold(self):
        self.env.ref("delivery.free_delivery_carrier").write({
            'name': 'Delivery Now Free Over 10',
            'fixed_price': 2,
            'free_over': True,
            'amount': 10,
        })
        self.env.ref("delivery.delivery_carrier").write({
            'sequence': 9999,  # ensure last to load price async
            'website_published': True,
        })
        # Ensure "Wire Transfer" is the default acquirer.
        # Acquirers are sorted by state, showing `test` acquirers first (don't ask why).
        self.env.ref("payment.payment_acquirer_transfer").write({"state": "test"})

        self.start_tour("/", 'check_free_delivery', login="admin")
