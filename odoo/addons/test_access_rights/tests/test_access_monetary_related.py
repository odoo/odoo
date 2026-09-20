from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


class TestMonetaryAccess(TransactionCaseWithUserDemo):
    def test_monetary_access_create(self):
        user_admin = self.env.ref("base.user_admin")
        user_demo = self.user_demo.with_user(user_admin)

        new_user = user_demo.copy({"monetary": 1 / 3})
        self.assertEqual(
            new_user.currency_id.id,
            False,
            "no company on the partner yet, so no currency to round with",
        )
        new_user.partner_id.company_id = new_user.company_id

        self.assertEqual(
            new_user.currency_id,
            new_user.company_id.currency_id,
            "currency_id declares company_id.currency_id, so the write is seen at once",
        )
        self.assertEqual(
            new_user.monetary,
            1 / 3,
            "the value cached before the currency existed stays as it was cached",
        )

        self.env.invalidate_all()

        self.assertEqual(
            new_user.currency_id.rounding,
            0.01,
            "We now get the correct currency.",
        )
        self.assertEqual(
            new_user.monetary,
            0.33,
            "The value was rounded when added to the cache.",
        )
