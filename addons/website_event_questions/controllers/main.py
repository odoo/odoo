# -*- coding: utf-8 -*-

from openerp.addons.website_event.controllers.main import website_event


class website_event(website_event):

    def _process_registration_details(self, details):
        ''' Process data posted from the attendee details form. '''
        registrations = super(website_event, self)._process_registration_details(details)
        for registration in registrations:
            answer_ids = []
            for key, value in registration.iteritems():
                if key.startswith('answer_ids-'):
                    answer_ids.append([4, int(value)])
            registration['answer_ids'] = answer_ids
        return registrations
