from odoo.fields import Datetime, Date
from odoo.addons.hr.tests.common import TestHrCommon


class TestContractCalendars(TestHrCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_richard = cls.env['resource.calendar'].create({'name': 'Calendar of Richard'})
        cls.employee.resource_calendar_id = cls.calendar_richard
        # force old date to test new version to be created.
        cls.employee.version_id.date_version = Date.to_date('2015-01-01')

        cls.calendar_35h = cls.env['resource.calendar'].create({'name': '35h calendar'})

        cls.contract_cdd_values = {
            'date_version': Date.to_date('2016-01-01'),
            'contract_date_start': Date.to_date('2016-01-01'),
            'name': 'First CDD Contract for Richard',
            'resource_calendar_id': cls.calendar_35h.id,
            'wage': 5000.0,
        }

        cls.contract_fully_flexible_values = {
            'date_version': Date.to_date('2017-01-01'),
            'contract_date_start': Date.to_date('2017-01-01'),
            'name': 'Fully Flexible Contract for Richard',
            'resource_calendar_id': False,
            'wage': 5000.0,
        }

    def test_contract_state_incoming_to_open(self):
        # Employee's calendar should change
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_richard)
        cdd = self.employee.create_version(self.contract_cdd_values)
        self.assertEqual(self.employee.version_id.id, cdd.id, "The version of the employee should be updated to the last version.")
        self.assertEqual(self.employee.resource_calendar_id, cdd.resource_calendar_id, "The employee should have the calendar of its contract.")

    def test_set_fully_flexible_contract_should_change_resource_calendar(self):
        # Setting a running contract with fully flexible calendar should set the employee's calendar to False (fully flexible)
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_richard)
        flexijob = self.employee.create_version(self.contract_fully_flexible_values)
        self.assertEqual(self.employee.version_id.id, flexijob.id, "The version of the employee should be updated to the last version.")
        self.assertFalse(self.employee.resource_calendar_id, "The employee should have a fully flexible calendar.")

    def test_contract_transfer_leaves(self):

        def create_calendar_leave(start, end, resource=None):
            return self.env['resource.calendar.leaves'].create({
                'name': 'leave name',
                'date_from': start,
                'date_to': end,
                'resource_id': resource.id if resource else None,
                'calendar_id': self.employee.resource_calendar_id.id,
                'time_type': 'leave',
            })

        start = Datetime.to_datetime('2015-11-17 07:00:00')
        end = Datetime.to_datetime('2015-11-20 18:00:00')
        leave1 = create_calendar_leave(start, end, resource=self.employee.resource_id)

        start = Datetime.to_datetime('2015-11-25 07:00:00')
        end = Datetime.to_datetime('2015-11-28 18:00:00')
        leave2 = create_calendar_leave(start, end, resource=self.employee.resource_id)

        # global leave
        start = Datetime.to_datetime('2015-11-25 07:00:00')
        end = Datetime.to_datetime('2015-11-28 18:00:00')
        leave3 = create_calendar_leave(start, end)

        self.calendar_richard.transfer_leaves_to(self.calendar_35h, resources=self.employee.resource_id, from_date=Date.to_date('2015-11-21'))

        self.assertEqual(leave1.calendar_id, self.calendar_richard, "It should stay in Richard's calendar")
        self.assertEqual(leave3.calendar_id, self.calendar_richard, "Global leave should stay in original calendar")
        self.assertEqual(leave2.calendar_id, self.calendar_35h, "It should be transferred to the other calendar")

        # Transfer global leaves
        self.calendar_richard.transfer_leaves_to(self.calendar_35h, resources=None, from_date=Date.to_date('2015-11-21'))

        self.assertEqual(leave3.calendar_id, self.calendar_35h, "Global leave should be transfered")

    def test_calendar_no_desync(self):
        """ resource_calendar_id cannot be desync between employee and version last version """
        self.employee.create_version(self.contract_cdd_values)
        self.assertEqual(self.employee.resource_calendar_id, self.calendar_35h)
        self.assertEqual(self.employee.version_id.resource_calendar_id, self.calendar_35h)
        self.assertEqual(self.employee.version_ids[0].resource_calendar_id, self.calendar_richard)
        calendar_38h = self.env['resource.calendar'].create({'name': '38h calendar'})
        self.employee.resource_calendar_id = calendar_38h
        self.assertEqual(self.employee.version_id.resource_calendar_id, calendar_38h)
        self.assertEqual(self.employee.version_ids[0].resource_calendar_id, self.calendar_richard)
