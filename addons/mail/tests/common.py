# -*- coding: utf-8 -*-

import json
import time

from contextlib import contextmanager
from email.utils import formataddr
from functools import partial
from unittest.mock import patch

from odoo import api
from odoo.addons.base.models.ir_mail_server import IrMailServer
from odoo.addons.bus.models.bus import json_dump
from odoo.tests import common, tagged, new_test_user

mail_new_test_user = partial(new_test_user, context={'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'mail_notrack': True, 'no_reset_password': True})


class MockEmail(common.BaseCase):

    @contextmanager
    def mockGateway(self):
        self._mails = []
        self._mail_args = []

        def _build_email(self, *args, **kwargs):
            print('building', args, kwargs)
            self._mails.append(kwargs)
            self._mail_args.append(args)

        def _send_email(self, message, *args, **kwargs):
            print('sending', message['Message-Id'])
            return message['Message-Id']

        try:
            with patch.object(IrMailServer, 'connect', return_value=True), \
                    patch.object(IrMailServer, 'build_email', side_effect=_build_email) as build_email_method_mock, \
                    patch.object(IrMailServer, 'send_email', side_effect=_send_email) as send_email_method_mock:
                yield
        finally:
            pass


class MailCase(common.BaseCase):

    def format(self, template, to='groups@example.com, other@gmail.com', subject='Frogs',
               extra='', email_from='Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>',
               cc='', msg_id='<1198923581.41972151344608186760.JavaMail@agrolait.com>'):
        return template.format(to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)

    def format_and_process(self, template, email_from, to, subject='Frogs', extra='',  cc='', msg_id=False,
                           model=None, target_model='mail.test.gateway', target_field='name'):
        self.assertFalse(self.env[target_model].search([(target_field, '=', subject)]))
        if not msg_id:
            msg_id = "<%.7f-test@iron.sky>" % (time.time())

        mail = self.format(template, to=to, subject=subject, cc=cc, extra=extra, email_from=email_from, msg_id=msg_id)
        self.env['mail.thread'].with_context(mail_channel_noautofollow=True).message_process(model, mail)
        return self.env[target_model].search([(target_field, '=', subject)])

<<<<<<< HEAD
    @contextmanager
    def assertMailNotifications(self, **counters):
=======

class MailCase(common.BaseCase):

    @contextmanager
    def assertNotifications(self, **counters):
>>>>>>> b4fb012c41d... tmp brol prout
        """ Counters: 'partner_attribute': 'inbox' or 'email' """
        try:
            init = {}
            partners = self.env['res.partner']
            for partner_attribute in counters.keys():
                partners |= getattr(self, partner_attribute)
            init_notifs = self.env['mail.notification'].sudo().search([('res_partner_id', 'in', partners.ids)])
            for partner in partners:
                if partner.user_ids:
                    init[partner] = {
                        'na_counter': len([n for n in init_notifs if n.res_partner_id == partner and not n.is_read]),
                    }
            yield
        finally:
            new_notifications = self.env['mail.notification'].sudo().search([
                ('res_partner_id', 'in', partners.ids),
                ('id', 'not in', init_notifs.ids)
            ])
            new_messages = new_notifications.mapped('mail_message_id')

            for partner_attribute in counters.keys():
                counter, notif_type, notif_read = counters[partner_attribute]
                partner = getattr(self, partner_attribute)
                partner_notif = new_notifications.filtered(lambda n: n.res_partner_id == partner)

                self.assertEqual(len(partner_notif), counter)

                if partner.user_ids:
                    expected = init[partner]['na_counter'] + counter if notif_read == 'unread' else init[partner]['na_counter']
                    real = self.env['mail.notification'].sudo().search_count([
                        ('res_partner_id', '=', partner.id),
                        ('is_read', '=', False)
                    ])
                    self.assertEqual(expected, real, 'Invalid number of notification for %s: %s instead of %s' %
                                                     (partner.name, real, expected))
                if partner_notif:
                    self.assertTrue(all(n.is_email == (notif_type == 'email') for n in partner_notif))
                    self.assertTrue(all(n.is_read == (notif_read == 'read') for n in partner_notif),
                                    'Invalid read status for %s' % partner.name)

            # for simplification, limitate to single message asserts
            if hasattr(self, 'assertEmails') and len(new_messages) == 1:
                self.assertEmails(new_messages.author_id, new_notifications.filtered(lambda n: n.is_email).mapped('res_partner_id'))

<<<<<<< HEAD

=======
>>>>>>> b4fb012c41d... tmp brol prout
    def assertBusNotification(self, channels, message_dicts=None, init=True):
        """ Check for bus notifications. Basic check is about used channels.
        Verifying content is optional.

        :param channels: list of channel
        :param messages: if given, list of message making a valid pair (channel,
          message) to be found in bus.bus
        """
        if init:
            self.assertEqual(len(self.env['bus.bus'].search([])), len(channels))
        notifications = self.env['bus.bus'].search([('channel', 'in', [json_dump(channel) for channel in channels])])
        self.assertEqual(len(notifications), len(channels))
        if message_dicts:
            notif_messages = [json.loads(n.message) for n in notifications]
            for expected in message_dicts:
                found = False
                for returned in notif_messages:
                    for key, val in expected.items():
                        if key not in returned:
                            continue
                        if isinstance(returned[key], list):
                            if set(returned[key]) != set(val):
                                continue
                        else:
                            if returned[key] != val:
                                continue
                            found = True
                            break
                    if found:
                        break
                if not found:
<<<<<<< HEAD
                    raise AssertionError("Bus notification content %s not found" % (repr(expected)))
=======
                    raise AssertionError("Bus notification content %s not found" % (repr(expected)))
>>>>>>> b4fb012c41d... tmp brol prout
