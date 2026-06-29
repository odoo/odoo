# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from psycopg2.errors import SerializationFailure

from odoo import SUPERUSER_ID, api
from odoo.modules.registry import Registry
from odoo.tests import TransactionCase, get_db_name, tagged
from odoo.tools import mute_logger

from odoo.addons.mail.models.mail_notification import MailNotification


@tagged('database_breaking')
class TestMessagePostConcurrent(TransactionCase):
    """Test suite to verify the behavior of message posting and mail sending under concurrent transaction scenarios.
    Specifically, it ensures that database serialization failures do not leave the database cr in an aborted state.
    """

    def setUp(self):
        """Set up the test environment by initializing a new database cr and creating a test message with
        its associated mail and notifications. The transaction is explicitly committed to persist these records in
        the database for the concurrent update simulation.
        """
        super().setUp()
        self.to_delete = []
        registry = Registry(get_db_name())
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            partner = env['res.partner'].search([], limit=1)
            message = partner.message_post(
                body='Hello',
                message_type='comment',
                partner_ids=[partner.id],
                mail_auto_delete=False,
                force_send=False,
            )
            notifs = env['mail.notification'].search(
                [('notification_type', '=', 'email'), ('mail_mail_id', 'in', message.mail_ids.ids)]
            )
            self.assertTrue(notifs)
            self.to_delete.extend([notifs, message.mail_ids, message])
            self.mails = message.mail_ids

    def tearDown(self):
        """Clean up the test environment by removing all records created during the setUp phase using a fresh
        database cursor, ensuring no residual data is left in the test database.
        """
        super().tearDown()
        registry = Registry(get_db_name())
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            for to_delete in self.to_delete:
                env[to_delete._name].browse(to_delete.ids).unlink()

    def test_mail_send_dirty_cursor(self):
        """Test SerializationFailure during flush does not leave the current transaction
        in an aborted state

        When updating mail notifications during `mail.mail._send()`, a SerializationFailure raised while
        flushing the notification recordset could leave the transaction aborted.
        As `_send()` continues handling the exception, accessing fields could cause any subsequent SQL query
        to fail with `InFailedSqlTransaction`, masking the original error.

        This test simulates a concurrency failure during `flush_recordset()` by modifying the same notification
        records in a separate transaction thread.
        It verifies that the original transaction recovers gracefully (via savepoints), raises the expected
        concurrency error, and ensures the cursor remains usable for subsequent ORM queries.

        As `_send()` continues handling the exception, accessing fields:
        - https://github.com/odoo/odoo/blob/127f1316540ec6cc68/addons/mail/models/mail_mail.py#L816
        """

        original_flush_recordset = MailNotification.flush_recordset

        def mocked_mail_notification_flush_recordset(self, *vals, **kwargs):
            registry = Registry(get_db_name())
            with registry.cursor() as cr:
                cr.execute(
                    'UPDATE mail_notification SET failure_reason = \'CONCURRENT UPDATE\' WHERE id IN %s',
                    (tuple(self.ids),),
                )
            return original_flush_recordset(self, *vals, **kwargs)

        notif_flush_meth = 'odoo.addons.mail.models.mail_notification.MailNotification.flush_recordset'
        registry = Registry(get_db_name())
        with (
            patch(notif_flush_meth, autospec=True, side_effect=mocked_mail_notification_flush_recordset),
            registry.cursor() as cr,
            mute_logger('odoo.addons.mail.models.mail_mail'),
            mute_logger('odoo.sql_db'),
        ):
            env = api.Environment(cr, SUPERUSER_ID, {})
            mails = env[self.mails._name].browse(self.mails.ids)
            with self.assertRaisesRegex(SerializationFailure, r'^could not serialize access due to concurrent update$'):
                mails.send()
            notifs = env['mail.notification'].search(
                [('notification_type', '=', 'email'), ('mail_mail_id', 'in', mails.ids)]
            )
            self.assertEqual(mails.state, 'exception')
            self.assertIn('concurrent access', notifs.failure_reason)
