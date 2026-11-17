from datetime import datetime, timedelta

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestEventTicketDatesWebsite(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        day_1 = datetime.combine(datetime.today() + timedelta(days=10), datetime.min.time())
        cls.event = cls.env['event.event'].create({
            'name': 'Conference',
            'date_begin': day_1 + timedelta(hours=8),
            'date_end': day_1 + timedelta(days=2, hours=18),
            'date_tz': 'UTC',
            'website_published': True,
            'event_ticket_ids': [
                (0, 0, {'name': 'Conference Pass'}),
                (0, 0, {
                    'name': 'MasterClass',
                    'date_begin': day_1 - timedelta(days=2, hours=-9),
                    'date_end': day_1 - timedelta(days=1, hours=-17),
                }),
            ],
        })
        cls.ticket_pass, cls.ticket_master = cls.event.event_ticket_ids.sorted('id')

    def test_ticket_modal_shows_ticket_dates(self):
        html = self.url_open(f'/event/{self.event.id}/register').text
        self.assertIn('MasterClass', html)
        self.assertEqual(html.count('o_wevent_ticket_validity'), 1, "Only the dated ticket shows its dates")

    def test_calendar_urls(self):
        urls = self.event._get_event_resource_urls(ticket=self.ticket_master)
        self.assertIn(f'ticket_id={self.ticket_master.id}', urls['iCal_url'])
        self.assertIn(self.ticket_master.date_begin.strftime('%Y%m%dT%H%M%S'), urls['google_url'])
        urls = self.event._get_event_resource_urls()
        self.assertNotIn('ticket_id', urls['iCal_url'])
        self.assertIn(self.event.date_begin.strftime('%Y%m%dT%H%M%S'), urls['google_url'])

        response = self.url_open(f"/event/{self.event.id}/ics?ticket_id={self.ticket_master.id}")
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.ticket_master.date_begin.strftime('%Y%m%dT%H%M%S'), response.text)
        other_event = self.event.copy()
        response = self.url_open(f"/event/{self.event.id}/ics?ticket_id={other_event.event_ticket_ids[:1].id}")
        self.assertEqual(response.status_code, 404, "A ticket of another event is refused")
