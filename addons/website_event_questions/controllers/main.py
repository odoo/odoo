# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEvent(WebsiteEventController):

    def _process_attendees_form(self, event, form_details):
        ''' Process data posted from the attendee details form. '''
        registrations = super(WebsiteEvent, self)._process_attendees_form(event, form_details)
        for registration in registrations:
            answer_ids = []
            for key, value in registration.items():
                if key.startswith('answer_ids-'):
                    answer_ids.append([4, int(value)])
            registration['answer_ids'] = answer_ids
        return registrations
