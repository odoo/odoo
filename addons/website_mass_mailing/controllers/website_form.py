import json

from odoo import _
from odoo.http import request
from odoo.libs.debug_log import DebugLog

from odoo.addons.website.controllers.form import WebsiteForm

_debug = DebugLog(__name__)


class WebsiteNewsletterForm(WebsiteForm):
    def _handle_website_form(self, model_name, **kwargs):
        if model_name == "mailing.contact":
            list_ids = kwargs.get("list_ids")
            if not list_ids:
                return json.dumps({"error": _("Mailing List(s) not found!")})
            list_ids = [int(x) for x in list_ids.split(",")]
            private_list_ids = (
                request.env["mailing.list"]
                .sudo()
                .search([("id", "in", list_ids), ("is_public", "=", False)])
            )
            if private_list_ids:
                _debug.logic(
                    "newsletter_private_lists_refused",
                    requested=len(list_ids),
                    private=private_list_ids,
                )
                return json.dumps(
                    {
                        "error": _(
                            "You cannot subscribe to the following list anymore : %s",
                            ", ".join(private_list_ids.mapped("name")),
                        )
                    }
                )
        return super()._handle_website_form(model_name, **kwargs)
