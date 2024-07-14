# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime

from odoo.tests import tagged, TransactionCase

@tagged('-at_install', 'post_install', 'work_entry_planning')
class TestWorkEntryPlanning(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Tom Clauz',
        })
        # While work entry generation via planning is handled in this module
        # hourly wages are defined in the payroll module
        cls.contract = cls.env['hr.contract'].create({
            'name': 'Tom Clauz\'s contract',
            'employee_id': cls.employee.id,
            'wage': 3500,
            'work_entry_source': 'planning',
            'date_start': '2020-01-01',
            'state': 'open',
        })

    def test_basic_generation(self):
        # Generates a slot for the afternoon every day of september 2021
        planning_slot_vals = []
        for i in range(1, 31):
            new_date = datetime(2021, 9, i, 13, 0, 0)
            if new_date.weekday() >= 5:
                continue
            planning_slot_vals.append({
                'resource_id': self.employee.resource_id.id,
                'start_datetime': new_date,
                'end_datetime': new_date.replace(hour=17),
            })
        slots = self.env['planning.slot'].create(planning_slot_vals)
        # Publishing the slots should not create any work entries for our employee since
        # we do not have an already generated period yet
        slots.action_planning_publish_and_send()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(work_entries)
        # This should generate one work entry per slot
        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))

        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(slots), len(work_entries))
        self.assertTrue(all(hwe.planning_slot_id for hwe in work_entries))

    def test_duplicate_slot(self):
        # Tests that two slots that are the same/overlap still generate multiple work entries
        slots = self.env['planning.slot'].create([
            # Same slots
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 14, 13, 0, 0),
                'end_datetime': datetime(2021, 9, 14, 17, 0, 0),
            },
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 14, 13, 0, 0),
                'end_datetime': datetime(2021, 9, 14, 17, 0, 0),
            },
            # Slots overlapping
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 15, 13, 0, 0),
                'end_datetime': datetime(2021, 9, 15, 17, 0, 0),
            },
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 15, 16, 0, 0),
                'end_datetime': datetime(2021, 9, 15, 19, 0, 0),
            },
            # Slots on boundaries
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 16, 13, 0, 0),
                'end_datetime': datetime(2021, 9, 16, 17, 0, 0),
            },
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 16, 17, 0, 0),
                'end_datetime': datetime(2021, 9, 16, 19, 0, 0),
            },
        ])
        slots.action_planning_publish_and_send()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(work_entries)

        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        # One work entry per slot
        self.assertEqual(len(work_entries), len(slots))
        # Each slot should have been assigned to one work entry
        self.assertEqual(len(work_entries.mapped('planning_slot_id')), len(slots.ids))

    def test_slot_within_period(self):
        # Tests that a slot created/published within the already generated period
        # is still created in the work entries
        boundaries_slots = self.env['planning.slot'].create([
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 1, 14, 0, 0),
                'end_datetime': datetime(2021, 9, 1, 17, 0, 0),
            },
            {
                'resource_id': self.employee.resource_id.id,
                'start_datetime': datetime(2021, 9, 30, 14, 0, 0),
                'end_datetime': datetime(2021, 9, 30, 17, 0, 0),
            }
        ])
        boundaries_slots.action_planning_publish_and_send()
        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(work_entries), len(boundaries_slots))

        inner_slot = self.env['planning.slot'].create({
            'resource_id': self.employee.resource_id.id,
            'start_datetime': datetime(2021, 9, 14, 14, 0, 0),
            'end_datetime': datetime(2021, 9, 14, 17, 0, 0),
        })
        inner_slot.action_send()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertEqual(len(boundaries_slots) + len(inner_slot), len(work_entries))

    def test_publish_unpublish(self):
        # Tests that a slot being unpublished archives the slot
        slot = self.env['planning.slot'].create({
            'resource_id': self.employee.resource_id.id,
            'start_datetime': datetime(2021, 9, 14, 14, 0, 0),
            'end_datetime': datetime(2021, 9, 14, 17, 0, 0),
        })
        # Cheat a bit by manually setting a generated period
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        # Should create a work entry
        slot.action_send()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(work_entries)
        # Should archive the above created work entry
        slot.action_unpublish()
        self.assertFalse(work_entries.active)
        # Should recreate a new work entry
        slot.action_send()
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(work_entries)
        # Should archive the new work entry
        slot.unlink()
        self.assertFalse(work_entries.active)

    def test_work_entry_uses_slot_duration(self):
        # Tests that a work entry uses the slot duration instead of computing it itself.
        slot = self.env['planning.slot'].create({
            'resource_id': self.employee.resource_id.id,
            'start_datetime': datetime(2021, 9, 6, 0, 0, 0),
            'end_datetime': datetime(2021, 9, 10, 23, 59, 59),
            'allocated_hours': 38,
        })
        slot.action_send()
        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertTrue(work_entries)
        self.assertEqual(work_entries.duration, slot.allocated_hours)

    def test_invalid_contract(self):
        # Tests that slots don't generate work entries if the contract isn't in planning mode
        self.contract.write({
            'work_entry_source': 'calendar',
        })
        self.env['planning.slot'].create({
            'resource_id': self.employee.resource_id.id,
            'start_datetime': datetime(2021, 9, 14, 14, 0, 0),
            'end_datetime': datetime(2021, 9, 14, 17, 0, 0),
            'state': 'published',
        })
        self.contract.generate_work_entries(date(2021, 9, 1), date(2021, 9, 30))
        work_entries = self.env['hr.work.entry'].search([('employee_id', '=', self.employee.id)])
        self.assertFalse(any(hwe.planning_slot_id for hwe in work_entries))

    def test_create_work_entries(self):
        """ No assertion in this test, the purpose is just to check that
            plannings_slots._create_work_entries() happens without raising error
            when one of the slots is related to work_entries and the other not.
        """
        self.contract.write({
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        employee2 = self.env['hr.employee'].create({
            'name': 'Santa Cruise',
        })
        self.env['hr.contract'].create({
            'name': 'Santa Cruise\'s contract',
            'employee_id': employee2.id,
            'wage': 5300,
            'work_entry_source': 'planning',
            'date_start': '2020-01-01',
            'state': 'open',
            'date_generated_from': datetime(2021, 9, 1, 0, 0, 0),
            'date_generated_to': datetime(2021, 9, 30, 23, 59, 59),
        })
        planning_slots = self.env['planning.slot'].create([{
            'resource_id': self.employee.resource_id.id,
            'start_datetime': datetime(2021, 9, 14, 14, 0, 0),
            'end_datetime': datetime(2021, 9, 14, 17, 0, 0),
        }, {
            'resource_id': employee2.resource_id.id,
            'start_datetime': datetime(2021, 9, 15, 14, 0, 0),
            'end_datetime': datetime(2021, 9, 15, 17, 0, 0),
        }])
        self.env['hr.work.entry'].create({
            'name': 'Mission Impossible: Distribute Gifts',
            'employee_id': employee2.id,
            'contract_id': employee2.contract_id.id,
            'date_start': datetime(2021, 9, 15, 14, 0, 0),
            'date_stop': datetime(2021, 9, 15, 17, 0, 0),
        })
        planning_slots._create_work_entries()
