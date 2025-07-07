from odoo.exceptions import ValidationError

from odoo.addons.test_resource.tests.common import TestResourceCommon


class TestErrors(TestResourceCommon):
    def setUp(self):
        super().setUp()

    def test_create_negative_leave(self):
        # from > to
        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'error cannot return in the past',
                'resource_id': False,
                'calendar_id': self.calendar_jean.id,
                'date_from': self.datetime_str(2018, 4, 3, 20, 0, 0, tzinfo=self.jean.tz),
                'date_to': self.datetime_str(2018, 4, 3, 0, 0, 0, tzinfo=self.jean.tz),
            })

        with self.assertRaises(ValidationError):
            self.env['resource.calendar.leaves'].create({
                'name': 'error caused by timezones',
                'resource_id': False,
                'calendar_id': self.calendar_jean.id,
                'date_from': self.datetime_str(2018, 4, 3, 10, 0, 0, tzinfo='UTC'),
                'date_to': self.datetime_str(2018, 4, 3, 12, 0, 0, tzinfo='Etc/GMT-6'),
            })
