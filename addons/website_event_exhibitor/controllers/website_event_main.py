# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from babel.dates import format_datetime

from odoo import _
from odoo.http import request
from odoo.addons.website_event.controllers import main


class WebsiteEventController(main.WebsiteEventController):
    def _prepare_event_register_values(self, event, **post):
        values = super(WebsiteEventController, self)._prepare_event_register_values(event, **post)

        if "from_sponsor_id" in post and not event.is_ongoing:
            sponsor = request.env["event.sponsor"].browse(int(post["from_sponsor_id"])).exists()
            if sponsor:
                date_begin = format_datetime(event.date_begin, format="medium", tzinfo=event.date_tz)

                values["toast_message"] = (
                    _('The event %s starts on %s (%s). \nJoin us there to meet %s!',
                    event.name, date_begin, event.date_tz, sponsor.partner_name)
                )

        return values
