# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import datetime
from freezegun import freeze_time

from odoo.addons.mail.tests.common import MailCase
from odoo.addons.microsoft_calendar.utils.microsoft_calendar import MicrosoftCalendarService
from odoo.addons.microsoft_calendar.models.res_users import ResUsers
from odoo.addons.microsoft_calendar.tests.common import TestCommon


class TestSyncOdoo2MicrosoftMail(TestCommon, MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.users = []
        for n in range(1, 3):
            user = cls.env['res.users'].create({
                'name': f'user{n}',
                'login': f'user{n}',
                'email': f'user{n}@odoo.com',
                'microsoft_calendar_rtoken': f'abc{n}',
                'microsoft_calendar_token': f'abc{n}',
                'microsoft_calendar_token_validity': datetime(9999, 12, 31),
            })
            user.res_users_settings_id.write({
                'microsoft_synchronization_stopped': False,
                'microsoft_calendar_sync_token': f'{n}_sync_token',
            })
            cls.users += [user]

    @freeze_time("2020-01-01")
    @patch.object(ResUsers, '_get_microsoft_calendar_token', lambda user: user.microsoft_calendar_token)
    def test_event_creation_for_user(self):
        """Check that either emails or synchronization happens correctly when creating an event for another user."""
        user_root = self.env.ref('base.user_root')
        self.assertFalse(user_root.microsoft_calendar_token)
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        event_values = {
            'name': 'Event',
            'need_sync_m': True,
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
        }
        for create_user, organizer, expect_mail in [
            (user_root, self.users[0], True), (user_root, None, True),
                (self.users[0], None, False), (self.users[0], self.users[1], False)]:
            with self.subTest(create_uid=create_user.name if create_user else None, user_id=organizer.name if organizer else None):
                with self.mock_mail_gateway(), patch.object(MicrosoftCalendarService, 'insert') as mock_insert:
                    mock_insert.return_value = ('1', '1')
                    self.env['calendar.event'].with_user(create_user).create({
                        **event_values,
                        'partner_ids': [(4, organizer.partner_id.id), (4, partner.id)] if organizer else [(4, partner.id)],
                        'user_id': organizer.id if organizer else False,
                    })
                    self.env.cr.postcommit.run()
                if not expect_mail:
                    self.assertNotSentEmail()
                    mock_insert.assert_called_once()
                    self.assert_dict_equal(mock_insert.call_args[0][0]['organizer'], {
                        'emailAddress': {'address': organizer.email if organizer else '', 'name': organizer.name if organizer else ''}
                    })
                else:
                    mock_insert.assert_not_called()
                    self.assertMailMail(partner, 'sent', author=(organizer or create_user).partner_id)
