from odoo.tests import tagged
from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleSettings(BaseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Test Company',
        })
        cls.website = cls.env['website'].create({
            'name': 'Test Website',
            'company_id': cls.company.id,
            'account_on_checkout': 'mandatory',
            'auth_signup_uninvited': 'b2b',
        })

    def test_settings_account_on_checkout(self):
        # only change auth_signup_uninvited if account_on_checkout was changed
        config = self.env['res.config.settings'].with_company(self.company)
        config.create({'account_on_checkout': 'mandatory'}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, 'b2b')
        config.create({'account_on_checkout': 'optional'}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, 'b2c')
        config.create({'account_on_checkout': 'disabled'}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, 'b2b')
        config.create({'auth_signup_uninvited': 'b2c', 'account_on_checkout': 'disabled'}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, 'b2c')
        config.create({'auth_signup_uninvited': 'b2b', 'account_on_checkout': 'mandatory'}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, 'b2c')
