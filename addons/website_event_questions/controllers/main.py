# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.website_event.controllers.main import WebsiteEventController


class WebsiteEvent(WebsiteEventController):

    def _process_attendees_form(self, event, form_details):
        """ Process data posted from the attendee details form.
        Extracts question answers:
        - For both questions asked 'once_per_order' and questions asked to every attendee
        - For questions of type 'simple_choice', extracting the suggested answer id
        - For questions of type 'text_box', extracting the text answer of the attendee. """
        registrations = super(WebsiteEvent, self)._process_attendees_form(event, form_details)

        for registration in registrations:
            registration['registration_answer_ids'] = []

        general_answer_ids = []
        for key, value in form_details.items():
            if 'question_answer' in key and value:
                dummy, registration_index, question_id = key.split('-')
                question_sudo = request.env['event.question'].browse(int(question_id))
                answer_values = None
                if question_sudo.question_type == 'simple_choice':
                    answer_values = {
                        'question_id': int(question_id),
                        'value_answer_id': int(value)
                    }
                elif question_sudo.question_type == 'text_box':
                    answer_values = {
                        'question_id': int(question_id),
                        'value_text_box': value
                    }

                if answer_values and not int(registration_index):
                    general_answer_ids.append((0, 0, answer_values))
                elif answer_values:
                    registrations[int(registration_index) - 1]['registration_answer_ids'].append((0, 0, answer_values))

        for registration in registrations:
            registration['registration_answer_ids'].extend(general_answer_ids)

        return registrations
