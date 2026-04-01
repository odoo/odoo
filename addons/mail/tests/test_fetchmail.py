# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta
from unittest.mock import patch

from odoo.tests import TransactionCase, mute_logger


class MockedConnection:
    def __init__(self):
        self.mock_messages = {}

    def check_unread_messages(self):
        return len(self.mock_messages)

    def retrieve_unread_messages(self):
        yield from list(self.mock_messages.items())

    def handled_message(self, num):
        self.mock_messages.pop(num)

    def disconnect(self):
        pass


class TestFetchmail(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # mock connection
        cls.connection = MockedConnection()

        def _connect__(self, allow_archived=False):
            self.ensure_one()
            return cls.connection
        patcher = patch.object(cls.registry['fetchmail.server'], '_connect__', _connect__)
        patcher.start()
        cls.addClassCleanup(patcher.stop)

    def setUp(self):
        self.connection.mock_messages.clear()
        return super().setUp()

    def test_fetchmail(self):
        mail_server = self.env['fetchmail.server'].create({
            'name': 'test server',
        })
        mail_server.search([('id', '!=', mail_server.id)]).action_archive()

        # confirm the server
        mail_server.button_confirm_login()
        self.assertEqual(mail_server.state, 'done')

        # fetch mail
        partner = self.env['res.partner'].create({'name': 'fetch test'})

        def message_process(obj, model, message, **kw):
            self.assertEqual(message, "test msg")
            partner.with_env(obj.env).name = 'processed'
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(self.registry['mail.thread'], 'message_process', side_effect=message_process, autospec=True) as process,
        ):
            self.connection.mock_messages[1] = "test msg"
            mail_server.with_env(mail_server.env(cr=cr)).fetch_mail()
            process.assert_called_once()
            self.assertFalse(self.connection.mock_messages, "message not handled")
        self.assertEqual(partner.name, 'processed', "message_process side effect should be saved")

    def test_fetchmail_deactivation(self):
        mail_server = self.env['fetchmail.server'].create({
            'name': 'test deactivation server',
        })
        mail_server.search([('id', '!=', mail_server.id)]).action_archive()
        mail_server.button_confirm_login()
        self.assertEqual(mail_server.state, 'done')

        # fetch mail
        connection_failed_exception = Exception("mocked connection that fails")

        def _connect__(obj, **kw):
            raise connection_failed_exception
        with (
            self.enter_registry_test_mode(),
            self.registry.cursor() as cr,
            patch.object(self.registry['fetchmail.server'], '_connect__', side_effect=_connect__, autospec=True),
            mute_logger('odoo.addons.mail.models'),
            self.assertLogs('odoo.addons.base.models.ir_cron') as cron_log_catcher,
        ):
            server = mail_server.with_env(mail_server.env(cr=cr))
            self.assertFalse(server.error_date)
            self.assertFalse(server.error_message)
            exc = server._fetch_mail()
            self.assertIs(exc, connection_failed_exception)
            self.assertTrue(server.error_date)
            self.assertIn("mocked connection", server.error_message)

            # set the date in past for deactivation
            server.error_date = server.error_date - timedelta(days=7, minutes=1)
            exc = server._fetch_mail()
            self.assertIs(exc, connection_failed_exception)
            self.assertEqual(server.state, 'draft')
            self.assertIn('WARNING:odoo.addons.base.models.ir_cron:Deactivating fetchmail imap server test deactivation server (too many failures)', cron_log_catcher.output)
