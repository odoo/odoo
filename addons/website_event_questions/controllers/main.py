# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEvent(WebsiteEventController):

    def _process_attendees_form(self, event, form_details):
        ''' Process data posted from the attendee details form. '''
        registrations = super(WebsiteEvent, self)._process_attendees_form(event, form_details)

        for registration in registrations:
            registration['answer_ids'] = []

        general_answer_ids = []
        for key, value in form_details.items():
            if 'answer_ids' in key:
                index = int(key.split('-')[0])
                if not index:
                    general_answer_ids.append([4, int(value)])
                else:
                    registrations[index-1]['answer_ids'].append([4, int(value)])

        for registration in registrations:
            registration['answer_ids'].extend(general_answer_ids)

        return registrations
