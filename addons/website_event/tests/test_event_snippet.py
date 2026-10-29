# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from freezegun import freeze_time

from odoo.addons.event.tests.common import EventCase
from odoo.tests import tagged, users

SNIPPET_TEMPLATES = [
    f'website_event.dynamic_filter_template_event_event_{layout}'
    for layout in ('picture', 'card', 'single_offset', 'single_entry', 'single_card', 'single_badge', 'single_aside')
]


@tagged('post_install', '-at_install')
class TestEventSnippet(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reference_now = datetime(2020, 7, 6, 10, 0, 0)
        cls.multi_slots_event = cls.env['event.event'].create({
            'name': 'Multi Slots Event',
            'date_begin': datetime(2020, 7, 1, 8, 0, 0),
            'date_end': datetime(2020, 8, 31, 18, 0, 0),
            'date_tz': 'UTC',
            'is_multi_slots': True,
            'seats_limited': True,
            'seats_max': 1,
            'website_published': True,
        })
        # Use different start hours to distinguish the dates in the rendered snippets
        cls.slot_past, cls.slot_sold_out, cls.slot_open, cls.slot_open_later = cls.env['event.slot'].create([{
            'event_id': cls.multi_slots_event.id,
            'date': slot_date,
            'start_hour': start_hour,
            'end_hour': start_hour + 1,
        } for slot_date, start_hour in (
            (date(2020, 7, 5), 10), (date(2020, 7, 7), 11), (date(2020, 7, 8), 14), (date(2020, 7, 9), 16),
        )])
        cls.env['event.registration'].create({
            'event_id': cls.multi_slots_event.id,
            'event_slot_id': cls.slot_sold_out.id,
            'name': 'Attendee',
        })

    @users('public_test')
    def test_snippet_templates_display_next_open_slot(self):
        """Check that all snippet layouts display the next available slot date."""
        snippet_filter = self.env.ref('website_event.website_snippet_filter_event_list_unfinished').sudo()

        def format_time(value):
            return self.env['ir.qweb.field.datetime'].value_to_html(
                value, {'time_only': True, 'format': 'short', 'tz_name': 'UTC'})

        expected_time = format_time(self.slot_open.start_datetime)
        unexpected_times = [format_time(value) for value in (
            self.multi_slots_event.date_begin, self.slot_past.start_datetime,
            self.slot_sold_out.start_datetime, self.slot_open_later.start_datetime,
        )]
        for template in SNIPPET_TEMPLATES:
            with self.subTest(template=template), freeze_time(self.reference_now):
                html = ''.join(snippet_filter._render(
                    template, 16, search_domain=[('id', '=', self.multi_slots_event.id)],
                    events_event_time_active=True,
                ))
                self.assertIn(expected_time, html)
                for unexpected_time in unexpected_times:
                    self.assertNotIn(unexpected_time, html)
