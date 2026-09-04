# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.calendar.tests.test_access_rights import TestAccessRights
from odoo.exceptions import AccessError
from odoo.tests import tagged


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestGoogleAccessRoles(TestAccessRights):

    def test_members_only_google_roles(self):
        members_only_event = self.create_event(self.george, name='members-only', privacy='members_only')
        self.assertEqual(members_only_event.calendar_id, self.george.primary_calendar_id)

        self.env['calendar.user'].with_user(self.george).create([
            {
                'calendar_id': self.george.primary_calendar_id.id,
                'user_id': self.john.id,
                'access_role': 'reader',
            },
            {
                'calendar_id': self.george.primary_calendar_id.id,
                'user_id': self.raoul.id,
                'access_role': 'freeBusyReader',
            },
        ])

        self.assertTrue(
            members_only_event.with_user(self.raoul)._check_private_event_conditions(),
            "Privacy check must be True because Raul doesn't have full access to the calendar."
        )
        with self.assertRaises(AccessError):
            members_only_event.with_user(self.raoul).write({'name': 'blocked-update'})

        self.assertFalse(
            members_only_event.with_user(self.john)._check_private_event_conditions(),
            "Privacy check must be False because John has reader access to the event calendar."
        )
        with self.assertRaises(AccessError):
            members_only_event.with_user(self.john).write({'name': 'blocked-update'})
