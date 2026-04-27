# Part of Odoo. See LICENSE file for full copyright and licensing details
from datetime import datetime, timedelta
from freezegun import freeze_time

from .common import TestPlanningContractCommon

class TestPlanningContract(TestPlanningContractCommon):

    @freeze_time('2024-03-11 08:00:00')
    def test_recurrence_permanent_contract(self):
        """
        This test covers the default use case in which a recurrent shift is planned inside of the employee contract date range.
        Specifically, the contract is a permanent one (it does not have an ending date).
        In this use case, the recurrent shifts will be planned normally until the end of the planning period. This is by default 6 months.
        """
        # This contract does not have a date_end, thus it is permanent.
        self.env['hr.contract'].create({
            'date_start': datetime.strptime('2024-01-01', '%Y-%m-%d'),
            'name': 'Long contract for Bert',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': self.employee_bert.id,
            'state': 'open',
        })
        recurrent_slot = self.env['planning.slot'].create({  # this should be a Monday
            'start_datetime': self.random_monday_date + timedelta(hours=15),
            'end_datetime': self.random_monday_date + timedelta(hours=16),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'forever',
            'repeat_interval': 1,
            'repeat_unit': 'week',
        })

        self.assertEqual(
            len(recurrent_slot.recurrency_id.slot_ids),
            27,  # There are 27 Mondays in the next 6 month period :(
            'Since the employee\'s contract is permanent, shifts will be planned for the next 6 months (the cron period).'
        )

    @freeze_time('2024-03-11 08:00:00')
    def test_recurrence_fixed_contract(self):
        """
        This test covers the use case in which a recurrent shift is planned inside of the employee contract date range,
        but the employee has a fixed term contract (it has an ending date).
        In this use case, the recurrent shifts will be planned normally until the end of the contract.
        """
        # This contract ends at the 27th of the month - it is a fixed term contract.
        self.env['hr.contract'].create({
            'date_end': datetime.strptime('2024-3-27', '%Y-%m-%d'),
            'date_start': datetime.strptime('2024-01-01', '%Y-%m-%d'),
            'name': 'Short contract for Bert',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': self.employee_bert.id,
            'state': 'open',
        })
        recurrent_slot = self.env['planning.slot'].create({  # this should land on a Monday
            'start_datetime': self.random_monday_date + timedelta(hours=15),
            'end_datetime': self.random_monday_date + timedelta(hours=16),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'forever',
            'repeat_interval': 1,
            'repeat_unit': 'week',
        })

        self.assertEqual(
            len(recurrent_slot.recurrency_id.slot_ids),
            3,  # There are 3 Mondays until the 27th of March :(
            'Since the employee\'s contract is fixed, shifts will be planned until the end of the contract.'
        )

    @freeze_time('2024-03-11 08:00:00')
    def test_recurrence_with_slot_outside_fixed_contract(self):
        """
        This test covers the use case in which the initial shift (to be repeated) is planned outisde of the employee contract date range.
        Specifically in the test case, the contract has ended prior to the slot's date.
        In this use case, the recurrent shifts will be planned again normally until the end of the planning period (6 months) as if it was within contract.
        """
        # This contract ends at the 8th of the month - it should already be over
        self.env['hr.contract'].create({  # Fixed term contract
            'date_end': datetime.strptime('2024-3-08', '%Y-%m-%d'),
            'date_start': datetime.strptime('2024-01-01', '%Y-%m-%d'),
            'name': 'Outdated contract for Bert',
            'resource_calendar_id': self.calendar_40h.id,
            'wage': 5000.0,
            'employee_id': self.employee_bert.id,
            'state': 'open',
        })
        recurrent_slot = self.env['planning.slot'].create({  # this should be a Monday
            'start_datetime': self.random_monday_date + timedelta(hours=15),
            'end_datetime': self.random_monday_date + timedelta(hours=16),
            'resource_id': self.resource_bert.id,
            'repeat': True,
            'repeat_type': 'forever',
            'repeat_interval': 1,
            'repeat_unit': 'week',
        })

        self.assertEqual(
            len(recurrent_slot.recurrency_id.slot_ids),
            27,
            'Since the initial shift was planned outside of the employee\'s contract, shifts will be planned normally for the next 6 months.'
        )
