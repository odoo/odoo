# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestWebsiteSaleSettings(BaseCommon):
    _test_user_groups = (
        'base.group_user',
        'website.group_website_designer',  # read/write website config in the test body
    )

    _test_user_name = 'Test User'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref('base.test_company')
        cls._test_user.company_ids |= cls.company
        cls.website = cls.env["website"].create({
            "name": "Test Website",
            "company_id": cls.company.id,
            "account_on_checkout": "mandatory",
            "auth_signup_uninvited": "b2b",
        })

    def test_settings_account_on_checkout(self):
        # only change auth_signup_uninvited if account_on_checkout was changed
        config = self.env["res.config.settings"].sudo().with_company(self.company)
        config.create({"account_on_checkout": "mandatory"}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, "b2b")
        config.create({"account_on_checkout": "optional"}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, "b2c")
        config.create({"account_on_checkout": "disabled"}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, "b2b")
        config.create({"auth_signup_uninvited": "b2c", "account_on_checkout": "disabled"}).execute()
        self.assertEqual(self.website.auth_signup_uninvited, "b2c")
        config.create({
            "auth_signup_uninvited": "b2b",
            "account_on_checkout": "mandatory",
        }).execute()
        self.assertEqual(self.website.auth_signup_uninvited, "b2c")
