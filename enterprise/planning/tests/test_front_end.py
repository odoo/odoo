# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.tests import tagged
from .test_ui_common import TestUiCommon


@tagged('-at_install', 'post_install')
class TestFrontEnd(TestUiCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.front_end_actor_role, cls.front_end_cameraman_role = cls.env['planning.role'].create([{
            'name': 'Actor',
            'color': 1,
        }, {
            'name': 'Camera Man',
            'color': 2,
        }])
        cls.front_end_slot = cls.env['planning.slot'].create({
            'start_datetime': datetime(2024, 5, 16, 8, 0, 0),
            'end_datetime': datetime(2024, 5, 16, 9, 0, 0),
            'state': 'published',
            'resource_id': cls.employee_thibault.resource_id.id,
            'role_id': cls.front_end_actor_role.id,
        })
        # Create a new planning
        cls.front_end_planning = cls.env['planning.planning'].create({
            'start_datetime': datetime(2024, 5, 15, 8, 0, 0) - relativedelta(days=1),
            'end_datetime': datetime(2024, 5, 15, 8, 0, 0) + relativedelta(days=2),
        })
        # delete all open slots - required for the tours below
        open_shifts = cls.env['planning.slot'].search([('resource_id', '=', False)])
        open_shifts.unlink()

    @freeze_time('2024-05-15 08:00:00')
    def test_front_end_ui(self):
        # Change the unavailable setting to "switch"
        self.env['res.config.settings'].create({
            'planning_employee_unavailabilities': 'switch',
        }).execute()
        self.front_end_open_slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2024, 5, 16, 10, 0, 0),
            'end_datetime': datetime(2024, 5, 16, 11, 0, 0),
            'state': 'published',
            'role_id': self.front_end_actor_role.id,
        })
        front_end_thibault_url = self.employee_thibault.sudo()._planning_get_url(self.front_end_planning)
        self.start_tour(front_end_thibault_url[self.employee_thibault.id], 'planning_front_end_tour')
        self.assertEqual(self.front_end_open_slot.resource_id.id, self.employee_thibault.resource_id.id, 'Thibault should now be assigned to the open shift')

    @freeze_time('2024-05-15 08:00:00')
    def test_front_end_allow_unassign_ui(self):
        # Change the unavailable setting to "unassign"
        self.env['res.config.settings'].create({
            'planning_employee_unavailabilities': 'unassign',
            'planning_self_unassign_days_before': 0,
        }).execute()
        front_end_thibault_url = self.employee_thibault.sudo()._planning_get_url(self.front_end_planning)
        self.start_tour(front_end_thibault_url[self.employee_thibault.id], 'planning_front_end_allow_unassign_tour')
        self.assertFalse(self.front_end_slot.resource_id, "Thibault's shift should now be an open slot")

    @freeze_time('2024-05-15 08:00:00')
    def test_front_end_email_buttons(self):
        # Change the unavailable setting to "unassign"
        self.env['res.config.settings'].create({
            'planning_employee_unavailabilities': 'unassign',
            'planning_self_unassign_days_before': 0,
        }).execute()
        # Add an open shift to the planning
        self.front_end_open_slot = self.env['planning.slot'].create({
            'start_datetime': datetime(2024, 5, 16, 10, 0, 0),
            'end_datetime': datetime(2024, 5, 16, 11, 0, 0),
            'state': 'published',
            'role_id': self.front_end_cameraman_role.id,
        })

        # --- Self Assign Button ---
        # Share the open slot with Thibault
        self.front_end_open_slot._send_slot(
            self.employee_thibault,
            self.front_end_open_slot.start_datetime,
            self.front_end_open_slot.end_datetime,
        )
        # Create a URL to immitate the "Assign me this shift" button click from the email received by Thibault
        front_end_thibault_assign_url = 'planning/%s/%s/assign/%s?message=1' % (
            self.front_end_planning.access_token,
            self.employee_thibault.sudo().employee_token,
            self.front_end_open_slot.id,
        )
        self.start_tour(front_end_thibault_assign_url, 'planning_front_end_buttons_tour')
        self.assertEqual(self.front_end_open_slot.resource_id.id, self.employee_thibault.resource_id.id, "Thibault should now be assigned to the open shift")

        # --- Unavailable Button ---
        # Share Thibault's slot with Thibault
        self.front_end_slot._send_slot(
            self.employee_thibault,
            self.front_end_slot.start_datetime,
            self.front_end_slot.end_datetime,
        )
        # Create a URL to immitate the "I am Unavailable" button click from the email received by Thibault
        front_end_thibault_unassign_url = 'planning/%s/%s/unassign/%s?message=1' % (
            self.front_end_planning.access_token,
            self.employee_thibault.sudo().employee_token,
            self.front_end_slot.id,
        )
        self.start_tour(front_end_thibault_unassign_url, 'planning_front_end_buttons_tour')
        self.assertFalse(self.front_end_slot.resource_id, "Thibault's shift should now be an open slot")
