# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import closing
import psycopg2
from odoo import api
from odoo.addons.test_mail.tests import common as mail_common
from odoo.tests import common
from odoo.tools import mute_logger

class TestMailRace(common.TransactionCase, mail_common.MockEmails):

    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mail_bounce_during_send(self):
        self.partner = self.env['res.partner'].create({
            'name': 'Ernest Partner',
        })
        # we need to simulate a mail sent by the cron task, first create mail, message and notification by hand
        mail = self.env['mail.mail'].create({
            'body_html': '<p>Test</p>',
            'notification': True,
            'state': 'outgoing',
            'recipient_ids': [(4, self.partner.id)]
        })
        message = self.env['mail.message'].create({
            'subject': 'S',
            'body': 'B',
            'subtype_id': self.ref('mail.mt_comment'),
            'needaction_partner_ids': [(6, 0, [self.partner.id])],
        })
        notif = self.env['mail.notification'].search([('res_partner_id', '=', self.partner.id)])
        notif.write({
            'mail_id': mail.id,
            'is_email': True,
            'is_read': True,
            'email_status': 'ready',
        })
        # we need to commit transaction or cr will keep the lock on notif
        self.cr.commit()

        # patch send_email in order to create a concurent update and check the notif is already locked by _send()
        this = self  # coding in javascript ruinned my life
        bounce_deferred = []
        @api.model
        def send_email(self, message, *args, **kwargs):
            with this.registry.cursor() as cr, mute_logger('odoo.sql_db'):
                try:
                    # try ro aquire lock (no wait) on notification (should fail)
                    cr.execute("SELECT email_status FROM mail_message_res_partner_needaction_rel WHERE id = %s FOR UPDATE NOWAIT", [notif.id])
                except psycopg2.OperationalError:
                    # record already locked by send, all good
                    bounce_deferred.append(True)
                else:
                    # this should trigger psycopg2.extensions.TransactionRollbackError in send().
                    # Only here to simulate the initial use case
                    # If the record is lock, this line would create a deadlock since we are in the same thread
                    # In practice, the update will wait the end of the send() transaction and set the notif as bounce, as expeced
                    cr.execute("UPDATE mail_message_res_partner_needaction_rel SET email_status='bounce' WHERE id = %s", [notif.id])
            return message['Message-Id']
        self.env['ir.mail_server']._patch_method('send_email', send_email)

        mail.send()

        self.assertTrue(bounce_deferred, "The bounce should have been deferred")
        self.assertEqual(notif.email_status, 'sent')

        # some cleaning since we commited the cr
        notif.unlink()
        message.unlink()
        mail.unlink()
        self.partner.unlink()
        self.env.cr.commit()
