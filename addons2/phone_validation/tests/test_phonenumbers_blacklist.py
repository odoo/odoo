# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("phone_blacklist")
class TestPhonenumbersBlacklist(TransactionCase):

    def test_sanitize_search(self):
        """ Test that when using search, the number is sanitized """
        blacklist = self.env['phone.blacklist']
        bl_entry = blacklist.create({'number': '+917589632587'})
        # be sure there is no company fallback for this test
        self.env.company.country_id = False

        for user_country in [
            self.env.ref("base.be"),  # other country (should work as complete number)
            self.env.ref("base.in"),  # correct country
            self.env["res.country"],  # no country
        ]:
            with self.subTest(country_name=user_country.name or "No country"):
                self.env.user.country_id = user_country

                res = blacklist.search([('number', 'in', ['+917 5896 32587'])])
                self.assertEqual(res, bl_entry)

                res = blacklist.search([('number', '=', '+917 5896 32587')])
                self.assertEqual(res, bl_entry)

                res = blacklist.search([('number', '=', '+917589632587')])
                self.assertEqual(res, bl_entry)
