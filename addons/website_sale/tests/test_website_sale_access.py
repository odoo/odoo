from odoo.fields import Command
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWebsiteSaleAccess(HttpCase):

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.website = self.env['website'].get_current_website()
        self.env['ir.ui.view'].search([
            ('key', '=', 'website_sale.products_categories')
        ]).active = True
        self.env['ir.ui.view'].search([
            ('key', '=', 'website_sale.option_collapse_products_categories')
        ]).active = False

        self.portal_user = self.env['res.users'].with_context(no_reset_password=True).create({
            'website_id': self.website.id,
            'login': 'portal_user',
            'name': 'Portal User',
            'group_ids': [Command.link(self.env.ref('base.group_portal').id)],
        })

    def test_public_and_portal_users_can_access_shop(self):
        """Public and Portal users should be able to access /shop without error"""
        response = self.url_open('/shop')
        self.assertEqual(response.status_code, 200)

        self.authenticate(self.portal_user.login, self.portal_user.login)
        response = self.url_open('/shop')
        self.assertEqual(response.status_code, 200)
