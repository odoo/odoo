# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.tests import TransactionCase, tagged

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_event_booth.controllers.event_booth import WebsiteEventBoothController


@tagged("post_install", "-at_install")
class TestEventBoothWebsite(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.lang_fr = cls.env["res.lang"]._activate_lang("fr_FR")
        cls.event = cls.env["event.event"].create(
            {
                "name": "Test Booth Event",
                "date_begin": datetime.today() + timedelta(days=1),
                "date_end": datetime.today() + timedelta(days=15),
            }
        )

    def test_booth_registration_public_user_lang(self):
        """Public booth registrant's contact must carry the active language."""
        with MockRequest(
            self.env(user=self.env.ref("base.public_user")),
            context={"lang": "fr_FR"},
        ):
            booth_values = WebsiteEventBoothController()._prepare_booth_registration_values(
                self.event,
                {
                    "contact_name": "Nouveau Exposant",
                    "contact_email": "new.exhibitor.fr@example.com",
                    "contact_phone": "+33123456789",
                },
            )
        self.assertTrue(booth_values["partner_id"])
        self.assertEqual(self.env["res.partner"].browse(booth_values["partner_id"]).lang, "fr_FR")
