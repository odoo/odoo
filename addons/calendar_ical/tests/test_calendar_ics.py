from odoo.tests import HttpCase


class TestCalendarICS(HttpCase):
    def setUp(self):
        super().setUp()
        user = self.env.ref('base.user_admin')
        self.key = self.env['res.users.apikeys'].with_user(user)._generate('calendar.ics', 'Calendar')
        self.url = f"{self.base_url()}/calendar.ics"

    def test_success(self):
        response = self.opener.get(self.url, params={'key': self.key})
        self.assertEqual(response.status_code, 200)
        self.assertRegex(response.text, r'^BEGIN:VCALENDAR')

    def test_bad_request(self):
        response = self.opener.get(self.url)
        self.assertEqual(response.status_code, 400)

    def test_unauthorized(self):
        response = self.opener.get(self.url, params={'key': 'bogus'})
        self.assertEqual(response.status_code, 401)

    def test_unacceptable(self):
        response = self.opener.get(self.url, params={'key': self.key}, headers={'Accept': 'image/jpeg'})
        self.assertEqual(response.status_code, 406)
