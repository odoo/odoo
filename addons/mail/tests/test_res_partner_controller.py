# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common_controllers import MailControllerCommon
from odoo.tests import tagged


@tagged("-at_install", "post_install", "mail_controller")
class TestResPartnerController(MailControllerCommon):

    def test_fetch_partners_no_fields(self):
        """Partners are returned with read access (internal users) or a valid mention token, and
        each request of a batched fetch is returned."""
        bob, zara = self.env["res.partner"].create([{"name": "Bob"}, {"name": "Zara"}])

        def fetch_partner_ids(user, tokens):
            self._authenticate_pseudo_user(user)
            data = self.make_jsonrpc_request(
                "/mail/data",
                {
                    "fetch_params": [
                        [
                            "partners_no_fields",
                            {
                                "partner_ids": [partner.id],
                                "partner_ids_mention_token": {str(partner.id): token},
                            },
                        ]
                        for partner, token in tokens
                    ],
                },
            )
            return {partner["id"] for partner in data.get("res.partner", [])}

        valid_tokens = [(bob, bob._get_mention_token()), (zara, zara._get_mention_token())]
        no_tokens = [(bob, ""), (zara, "")]
        self.assertEqual(fetch_partner_ids(self.user_portal, valid_tokens), {bob.id, zara.id})
        self.assertEqual(
            fetch_partner_ids(self.user_portal, [(bob, bob._get_mention_token()), (zara, "bad")]),
            {bob.id},
        )
        self.assertEqual(fetch_partner_ids(self.user_portal, no_tokens), set())
        self.assertEqual(fetch_partner_ids(self.user_public, no_tokens), set())
        self.assertEqual(fetch_partner_ids(self.user_employee, no_tokens), {bob.id, zara.id})
