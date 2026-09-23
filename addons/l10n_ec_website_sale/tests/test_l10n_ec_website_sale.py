from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEcWebsiteSale(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('ec')
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].create({
            'name': 'EC Website',
            'company_id': cls.company_data['company'].id,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Product', 'type': 'service', 'list_price': 50, 'taxes_id': False,
        })

    def test_cedula_required_above_final_consumer_limit(self):
        """Strictly above the limit a Cédula is required, and the checkout says why."""
        ec, step = self.env.ref('base.ec'), self.env['website.checkout.step']
        buyer = self.env['res.partner'].create({'name': "Juan Perez", 'country_id': ec.id})
        cart = self.env['sale.order'].sudo().create({
            'partner_id': buyer.id,
            'website_id': self.website.id,
            'order_line': [Command.create({'product_id': self.product.id})],
        })
        self.assertFalse(buyer._get_mandatory_additional_identifiers(ec, order_sudo=cart))

        self.website.l10n_ec_final_consumer_limit = 49.99
        self.assertEqual(buyer._get_mandatory_additional_identifiers(ec, order_sudo=cart), {'EC_DNI'})
        self.assertIn("order requires", step._get_billing_address_alert(cart))
        buyer.additional_identifiers = {'EC_DNI': '1714616123'}
        self.assertNotIn("identification", step._get_billing_address_alert(cart))
