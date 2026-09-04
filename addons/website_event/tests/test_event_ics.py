# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestEventIcs(HttpCase):

    def test_ics_file_matches_the_mail_language(self):
        """Check that the calendar file linked in the event subscription mail is written in the language of that mail."""
        self.env['res.lang']._activate_lang('fr_FR')
        self.env.ref('base.user_admin').lang = 'en_US'
        english_attendee, french_attendee = self.env['res.partner'].create([
            {'name': 'Kevin', 'lang': 'en_US'},
            {'name': 'Claire', 'lang': 'fr_FR'},
        ])
        event = self.env['event.event'].create({
            'name': 'Wood Workshop',
            'date_begin': datetime.now() + timedelta(days=1),
            'date_end': datetime.now() + timedelta(days=2),
            'registration_ids': [
                Command.create({'partner_id': english_attendee.id}),
                Command.create({'partner_id': french_attendee.id}),
            ],
        })
        event.with_context(lang='fr_FR').name = 'Atelier du bois'

        bodies = self.env.ref('event.event_subscription')._render_field(
            'body_html', event.registration_ids.ids, compute_lang=True)

        self.authenticate('admin', 'admin')
        summaries = {}
        for registration in event.registration_ids:
            ics_url = re.search(r'href="[^"]*(/event/[^"]+/ics[^"]*)"', bodies[registration.id]).group(1)
            summaries[registration.partner_id.lang] = self.url_open(ics_url).text

        self.assertIn('SUMMARY:Wood Workshop', summaries['en_US'])
        self.assertIn('SUMMARY:Atelier du bois', summaries['fr_FR'])
