# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Datetime as FieldsDatetime
from odoo.tools import frozendict
from odoo.tests.common import tagged

from odoo.addons.event_booth.tests.common import TestEventBoothCommon
from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.website_event_booth.controllers.event_booth import WebsiteEventBoothController


@tagged("post_install", "-at_install")
class TestEventBoothWebsite(TestEventBoothCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.lang_fr = cls.env["res.lang"]._activate_lang("fr_FR")
        cls.website = cls.env["website"].create(
            {
                "name": "Test Website",
                "default_lang_id": cls.env.ref("base.lang_en").id,
                "language_ids": [
                    (4, cls.env.ref("base.lang_en").id),
                    (4, cls.lang_fr.id),
                ],
            }
        )
        cls.event = cls.env["event.event"].create(
            {
                "name": "Test Booth Event",
                "date_begin": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=1)
                ),
                "date_end": FieldsDatetime.to_string(
                    datetime.today() + timedelta(days=15)
                ),
            }
        )
        cls.booth = cls.env["event.booth"].create(
            {
                "name": "Booth A",
                "booth_category_id": cls.event_booth_category_1.id,
                "event_id": cls.event.id,
            }
        )

    def test_booth_registration_public_user_lang(self):
        """When a public user registers for a booth from the website, the
        contact created for them must carry the active website language.
        """

        controller = WebsiteEventBoothController()
        contact_email = "new.exhibitor.fr@example.com"
        contact_name = "Nouveau Exposant"
        contact_phone = "+33123456789"

        public_user = self.env.ref("base.public_user")
        env_as_public = self.env(user=public_user)

        with MockRequest(
            env_as_public,
            website=self.website,
            context=frozendict({"lang": "fr_FR"}),
        ):
            booth_values = controller._prepare_booth_registration_values(
                self.event,
                {
                    "contact_name": contact_name,
                    "contact_email": contact_email,
                    "contact_phone": contact_phone,
                },
            )
        partner_id = booth_values.get("partner_id")
        assert partner_id, (
            "A partner should have been created for the public registrant"
        )
        partner = self.env["res.partner"].browse(partner_id)
        self.assertEqual(partner.lang, "fr_FR")
