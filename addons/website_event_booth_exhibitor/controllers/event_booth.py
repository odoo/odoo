import base64

from odoo.libs.debug_log import DebugLog
from odoo.tools import plaintext2html

from odoo.addons.website_event.controllers.main import WebsiteEventController

_debug = DebugLog(__name__)


class WebsiteEventBoothController(WebsiteEventController):
    def _prepare_booth_registration_values(self, event, kwargs):
        booth_values = super()._prepare_booth_registration_values(event, kwargs)
        if not booth_values.get("contact_email"):
            booth_values["contact_email"] = kwargs.get("sponsor_email")
        if not booth_values.get("contact_name"):
            booth_values["contact_name"] = kwargs.get("sponsor_name")
        if not self._phone_number_from_commands(booth_values.get("phone_ids")):
            booth_values["phone_ids"] = self._phone_number_commands(
                kwargs.get("sponsor_phone")
            )

        booth_values.update(
            **self._prepare_booth_registration_sponsor_values(
                event, booth_values, kwargs
            )
        )
        _debug.pipeline(
            "booth_sponsor_values",
            event=event,
            from_sponsor_email=bool(kwargs.get("sponsor_email")),
            from_sponsor_name=bool(kwargs.get("sponsor_name")),
            has_image=bool(kwargs.get("sponsor_image")),
        )
        return booth_values

    def _prepare_booth_registration_partner_values(self, event, kwargs):
        if not kwargs.get("contact_email") and kwargs.get("sponsor_email"):
            kwargs["contact_email"] = kwargs["sponsor_email"]
        if not kwargs.get("contact_name") and kwargs.get("sponsor_name"):
            kwargs["contact_name"] = kwargs["sponsor_name"]
        if not kwargs.get("contact_phone") and kwargs.get("sponsor_phone"):
            kwargs["contact_phone"] = kwargs["sponsor_phone"]
        return super()._prepare_booth_registration_partner_values(event, kwargs)

    def _prepare_booth_registration_sponsor_values(self, event, booth_values, kwargs):
        return {
            "sponsor_name": kwargs.get("sponsor_name")
            or booth_values.get("contact_name"),
            "sponsor_email": kwargs.get("sponsor_email")
            or booth_values.get("contact_email"),
            "sponsor_phone_ids": self._phone_number_commands(
                kwargs.get("sponsor_phone")
            )
            or booth_values.get("phone_ids"),
            "sponsor_subtitle": kwargs.get("sponsor_slogan"),
            "sponsor_website_description": plaintext2html(
                kwargs.get("sponsor_description")
            )
            if kwargs.get("sponsor_description")
            else "",
            "sponsor_image_512": base64.b64encode(kwargs["sponsor_image"].read())
            if kwargs.get("sponsor_image")
            else False,
        }
