# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.test_mail.tests import common
from odoo.tools import formataddr


class TestChannelPartnersNotification(common.MockEmails):

    def _join_channel(self, channel, partners):
        for partner in partners:
            channel.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': partner.id})]})
        channel.invalidate_cache()

    def test_channel_blacklisted_recipients(self):
        """ Posting a message on a channel should send one email to all recipients, except the blacklisted ones """

        self.test_channel = self.env['mail.channel'].create({
            'name': 'Test',
            'description': 'Description',
            'alias_name': 'test',
            'public': 'public',
        })
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Partner',
            'email': 'test@example.com',
        })

        self.blacklisted_partner = self.env['res.partner'].create({
            'name': 'Blacklisted Partner',
            'email': 'test@black.list',
        })

        # Set Blacklist
        self.env['mail.blacklist'].create({
            'email': 'test@black.list',
        })

        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        self.test_channel.write({'email_send': True})
        self._join_channel(self.test_channel, self.test_partner)
        self.test_channel.message_post(body="Test", message_type='comment', subtype='mt_comment')

        self.assertEqual(len(self._mails), 1, 'Number of mail incorrect. Should be equal to 1.')
        for email in self._mails:
            self.assertEqual(
                set(email['email_to']),
                set([formataddr((self.test_partner.name, self.test_partner.email))]),
                'email_to incorrect. Should be equal to "%s"' % (
                    formataddr((self.test_partner.name, self.test_partner.email))))
