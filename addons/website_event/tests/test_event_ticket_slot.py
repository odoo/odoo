from datetime import date, datetime, timedelta

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestEventTicketSlotWebsite(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        day_1 = date.today() + timedelta(days=10)
        day_2 = day_1 + timedelta(days=1)
        cls.event = cls.env['event.event'].create({
            'name': 'Two Days Festival',
            'date_begin': datetime.combine(day_1, datetime.min.time()),
            'date_end': datetime.combine(day_2, datetime.max.time().replace(microsecond=0)),
            'date_tz': 'UTC',
            'is_multi_slots': True,
            'website_published': True,
            'event_slot_ids': [
                (0, 0, {'date': day_1, 'start_hour': 9, 'end_hour': 18}),
                (0, 0, {'date': day_2, 'start_hour': 9, 'end_hour': 18}),
            ],
            'event_ticket_ids': [
                (0, 0, {'name': 'Full Access'}),
                (0, 0, {'name': 'Day One Pass'}),
            ],
        })
        cls.slot_1, cls.slot_2 = cls.event.event_slot_ids.sorted('date')
        cls.ticket_all = cls.event.event_ticket_ids.filtered(lambda t: t.name == 'Full Access')
        cls.ticket_day_1 = cls.event.event_ticket_ids - cls.ticket_all
        cls.ticket_day_1.event_slot_ids = cls.slot_1

    def test_website_confirm_refused(self):
        """ A crafted post (the modal never offers it) for an unlimited ticket
        on a slot it is not valid on goes back to the form with an error. """
        self.assertFalse(self.ticket_day_1.seats_limited)
        self.authenticate(None, None)
        response = self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            'csrf_token': self.csrf_token(),
            '1-event_slot_id': self.slot_2.id,
            '1-event_ticket_id': self.ticket_day_1.id,
        }, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        self.assertIn('registration_error_code=insufficient_seats', response.headers['Location'])
        self.assertFalse(self.event.registration_ids)

    def test_website_ticket_modal(self):
        url = f'/event/{self.event.id}/registration/slot/%s/tickets'
        html_day_1 = self.make_jsonrpc_request(url % self.slot_1.id, {})
        self.assertIn('Full Access', html_day_1)
        self.assertIn('Day One Pass', html_day_1)
        html_day_2 = self.make_jsonrpc_request(url % self.slot_2.id, {})
        self.assertIn('Full Access', html_day_2)
        self.assertNotIn('Day One Pass', html_day_2)
