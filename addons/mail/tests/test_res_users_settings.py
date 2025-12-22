# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import tagged, users, TransactionCase


class TestUSerCreationSettings(TransactionCase):

    def test_create_portal_user(self):
        portal_group = self.env.ref('base.group_portal')
        user = self.env.user.create({
            'name': 'A portal user',
            'login': 'portal_test',
            'groups_id': [(6, 0, [portal_group.id])],
        })
        self.assertFalse(user.res_users_settings_ids, 'Portal users should not have settings by default')

    def test_create_internal_user(self):
        user = self.env.user.create({
            'name': 'A internal user',
            'login': 'test_user',
        })
        self.assertTrue(user.res_users_settings_ids, 'Internal users should have settings by default')


@tagged("post_install", "-at_install")
class TestResUsersSettings(MailCommon):

    @users('employee')
    def test_find_or_create_for_user_should_create_record_if_not_existing(self):
        self.user_employee.res_users_settings_ids.unlink()  # pre autocreate or a portal user switching to internal user
        settings = self.user_employee.res_users_settings_ids
        self.assertFalse(settings, "no records should exist")

        self.env['res.users.settings']._find_or_create_for_user(self.user_employee)
        settings = self.user_employee.res_users_settings_ids
        self.assertTrue(settings, "a record should be created after _find_or_create_for_user is called")

    @users('employee')
    def test_find_or_create_for_user_should_return_correct_res_users_settings(self):
        self.user_employee.res_users_settings_ids.unlink()
        settings = self.env['res.users.settings'].create({
            'user_id': self.user_employee.id,
        })
        result = self.env['res.users.settings']._find_or_create_for_user(self.user_employee)
        self.assertEqual(result, settings, "Correct mail user settings should be returned")

    @users('employee')
    def test_set_res_users_settings_should_send_notification_on_bus(self):
        settings = self.user_employee.res_users_settings_id
        settings.is_discuss_sidebar_category_chat_open = False
        settings.is_discuss_sidebar_category_channel_open = False

        with self.assertBus(
                [(self.cr.dbname, 'res.partner', self.partner_employee.id)],
                [{
                    'type': 'res.users.settings',
                    'payload': {
                        'id': settings.id,
                        'is_discuss_sidebar_category_chat_open': True,
                    },
                }]):
            settings.set_res_users_settings({'is_discuss_sidebar_category_chat_open': True})

    @users('employee')
    def test_set_res_users_settings_should_set_settings_properly(self):
        settings = self.user_employee.res_users_settings_id
        settings.set_res_users_settings({'is_discuss_sidebar_category_chat_open': True})
        self.assertEqual(
            settings.is_discuss_sidebar_category_chat_open,
            True,
            "category state should be updated correctly"
        )
