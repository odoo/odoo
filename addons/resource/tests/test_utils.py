# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo.fields import Datetime
from odoo.tests.common import TransactionCase
from odoo.tests import tagged, Form


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestExpression(TransactionCase):

    def test_resource_calendar_leave_compute_date_to(self):
        """
        Test date_to is computed when date_from is changed,
        except when it already has a valid value.
        """
        date_from = Datetime.from_string('2024-05-01 00:00:00')
        date_to = Datetime.from_string('2024-05-03 23:59:59')
        leave = self.env['resource.calendar.leaves'].create({
            'date_from': date_from,
            'date_to': date_to,
        })

        leave.date_from -= relativedelta(minutes=5)
        self.assertEqual(leave.date_to, date_to, "date_to shouldn't get recomputed if still valid")

        leave.date_from += relativedelta(years=5)
        self.assertGreater(leave.date_to, date_to, "date_to should get recomputed when invalid")

    def test_resource_creation_with_date_from(self):
        """
        Test resource creation with a date_from.
        AssertError is raised when date_from is not provided.
        """

        with self.assertRaises(AssertionError):
            with Form(self.env['resource.calendar.leaves']) as res:
                res.date_from = False
                res.date_to = Datetime.now()

        with Form(self.env['resource.calendar.leaves']) as res:
            date_from = Datetime.now()
            date_to = Datetime.now() + relativedelta(hours=24)
            res.date_from = date_from
            res.date_to = date_to

            self.assertFalse(res.id, 'The resource does not have an id before saving')
            res.save()
            self.assertTrue(res.id, 'The resource was successfully created')
            self.assertEqual(res.date_from, Datetime.to_string(date_from))
            self.assertEqual(res.date_to, Datetime.to_string(date_to))
