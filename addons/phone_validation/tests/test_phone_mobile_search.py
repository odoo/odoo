from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPhoneMobileSearch(TransactionCase):
    """``phone_mobile_search`` must match on the sanitized (E164) form too.

    A contact's raw ``phone``/``mobile`` field can be typed in any local
    format; ``phone_sanitized`` normalizes it. Without including
    ``phone_sanitized`` among the fields consulted by
    ``_search_phone_mobile_search``, searching by the normalized form misses
    a contact whose raw number is stored differently.
    """

    def test_search_by_sanitized_form_matches_a_locally_stored_number(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Local-format contact",
                "phone_ids": [Command.create({"number": "012345678"})],
                "country_id": self.env.ref("base.be").id,
            }
        )
        self.assertEqual(partner.phone_sanitized, "+3212345678")
        # _search_phone_mobile_search runs raw SQL against the stored
        # columns, bypassing the ORM cache; flush so it sees this write.
        self.env.flush_all()

        found = self.env["res.partner"].search(
            [("phone_mobile_search", "=", "+3212345678")]
        )
        self.assertIn(partner, found)

    def test_a_list_of_terms_is_one_statement(self):
        # a display_name search with a list -- the import's parent lookup for
        # a batch of rows -- reaches the phone table once, not once per term
        be = self.env.ref("base.be").id
        partners = self.env["res.partner"].create(
            [
                {
                    "name": f"Listed contact {i}",
                    "phone_ids": [Command.create({"number": f"01234567{i}"})],
                    "country_id": be,
                }
                for i in range(3)
            ]
        )
        self.env.flush_all()
        Partner = self.env["res.partner"]
        with self.assertQueryCount(2):  # the phone lookup, then the partner search
            found = Partner.search(
                [("phone_mobile_search", "in", ["+3212345670", "+3212345672"])]
            )
        self.assertEqual(found, partners[0] + partners[2])
        with self.assertQueryCount(2):
            excluded = Partner.search(
                [
                    ("id", "in", partners.ids),
                    ("phone_mobile_search", "not in", ["+3212345670"]),
                ]
            )
        self.assertEqual(excluded, partners[1] + partners[2])
        self.assertEqual(
            Partner.search(
                [
                    ("phone_mobile_search", "in", ["+3212345670", False]),
                    ("id", "in", partners.ids),
                ]
            ),
            partners[0],
        )
