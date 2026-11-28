# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from lxml import html

from odoo.exceptions import ValidationError
from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestTrackLocation(HttpCase):
    """ A track shown in several locations: its main location and other ones. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        start = (datetime.now() + timedelta(days=5)).replace(hour=9, minute=0, second=0, microsecond=0)
        cls.start = start
        cls.event = cls.env['event.event'].create({
            'name': 'Retransmitted Conf',
            'date_begin': start,
            'date_end': start + timedelta(days=3),
            'date_tz': 'UTC',
            'website_published': True,
            'website_track': True,
        })
        cls.main_location, cls.overflow_1, cls.overflow_2, cls.other_location = cls.env['event.track.location'].create([
            {'name': 'Auditorium', 'sequence': 1},
            {'name': 'Overflow One', 'sequence': 2},
            {'name': 'Overflow Two', 'sequence': 3},
            {'name': 'Workshop Hall', 'sequence': 4},
        ])
        cls.stage = cls.env['event.track.stage'].search([('is_visible_in_agenda', '=', True)], limit=1)
        cls.keynote = cls._create_track(
            'Opening Keynote', 0, 1, cls.main_location,
            extra_location_ids=[(6, 0, (cls.overflow_1 | cls.overflow_2).ids)])
        cls.workshop = cls._create_track('Hands-on Workshop', 0, 1, cls.other_location, hours=2)

    @classmethod
    def _create_track(cls, name, day, duration, location, hours=0, **vals):
        return cls.env['event.track'].create({
            'name': name,
            'event_id': cls.event.id,
            'date': cls.start + timedelta(days=day, hours=hours),
            'duration': duration,
            'location_id': location.id,
            'stage_id': cls.stage.id,
            'is_published': True,
            **vals,
        })

    def test_all_locations(self):
        self.assertEqual(
            self.keynote.all_location_ids,
            self.main_location | self.overflow_1 | self.overflow_2)
        Track = self.env['event.track']
        domain = [('event_id', '=', self.event.id)]
        self.assertEqual(Track.search(domain + [('all_location_ids', 'in', self.overflow_1.ids)]), self.keynote)
        self.assertEqual(Track.search(domain + [('all_location_ids', 'in', self.main_location.ids)]), self.keynote)
        self.assertEqual(Track.search(domain + [('all_location_ids', 'in', self.other_location.ids)]), self.workshop)

    def test_constraints(self):
        with self.assertRaises(ValidationError):
            self.keynote.extra_location_ids = self.main_location
        with self.assertRaises(ValidationError):
            self.workshop.write({'location_id': False, 'extra_location_ids': [(4, self.overflow_1.id)]})

    def test_agenda(self):
        response = self.url_open(f'/event/{self.event.id}/agenda')
        self.assertEqual(response.status_code, 200)
        tree = html.fromstring(response.text)
        headers = [th.text_content().strip() for th in tree.xpath("//th[contains(@class, 'o_we_online_agenda_header_location')]")]
        self.assertEqual(headers, ['Auditorium', 'Overflow One', 'Overflow Two', 'Workshop Hall'])
        keynote_cells = tree.xpath("//td[contains(@class, 'event_track')][.//*[contains(text(), 'Opening Keynote')]]")
        self.assertEqual(len(keynote_cells), 3, "The keynote is shown in its location and in both other locations")
        self.assertFalse(any(cell.get('colspan') for cell in keynote_cells))
        self.assertEqual(len([cell for cell in keynote_cells if 'Live from Auditorium' in cell.text_content()]), 2)
        workshop_cells = tree.xpath("//td[contains(@class, 'event_track')][.//*[contains(text(), 'Hands-on Workshop')]]")
        self.assertEqual(len(workshop_cells), 1)
        # every row of the grid keeps the same width: time column + 4 locations
        for row in tree.xpath("//table//tr[td]"):
            if len(row.xpath("./td[contains(@class, 'event_track')]")) == 3:
                self.assertEqual(len(row.xpath('./td')), 5)

    def test_location_display(self):
        self.keynote.date = datetime.now() + timedelta(minutes=30)
        self.event.write({
            'date_begin': datetime.now() - timedelta(hours=1),
            'date_end': datetime.now() + timedelta(days=1),
        })
        for location in (self.main_location, self.overflow_1):
            response = self.url_open(f'/event/{self.event.id}/location-display/{location.id}')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Opening Keynote', response.text, f'Keynote missing on the {location.name} display')
        response = self.url_open(f'/event/{self.event.id}/location-display/{self.other_location.id}')
        self.assertNotIn('Opening Keynote', response.text)

    def test_track_page_and_list(self):
        response = self.url_open(f'/event/{self.event.id}/track/{self.keynote.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('also shown in', response.text)
        self.assertIn('Overflow One, Overflow Two', response.text)
        response = self.url_open(f'/event/{self.event.id}/track')
        self.assertEqual(response.status_code, 200)
        self.assertIn('+ Overflow One, Overflow Two', ' '.join(response.text.split()))
