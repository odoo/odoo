# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.test_mass_mailing.tests.common import MassMailingCase
from email.utils import formataddr
import datetime


class TestMassMailSubscriptions(MassMailingCase):
    """ Those tests are related to sending mass mailing (mail in mass_mode),
        with or without using the composer but in context of opted-out and/or blacklisted contacts
        (mm_contacts, mm_lists, res_partners, mail_channel_partners)
        It also checks that the auto blacklist and reset bounce rules are working properly. """

    def _join_channel(self, channel, partners):
        for partner in partners:
            channel.write({'channel_last_seen_partner_ids': [(0, 0, {'partner_id': partner.id})]})
        channel.invalidate_cache()

    def setUp(self):
        """ In this setup we prepare all the mailing contacts, mailing list and opt out entries.
        In order to test each configuration possible in the following tests. """
        super(TestMassMailSubscriptions, self).setUp()

        # create mailing contacts records
        self.contact_values = [{
            'name': 'Recipient %s' % x,
            'email': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 5)]
        self.mm_recs = self.env['mail.mass_mailing.contact'].create(self.contact_values)
        self.mm_partners = self.env['res.partner'].create([self.contact_values[x] for x in range(2, 5)])

        # create mailing lists records
        list_values = [{
            'name': 'Test list %s' % x,
            'contact_ids': [
                (4, self.mm_recs.ids[0]),
                (4, self.mm_recs.ids[1])
            ]
        } for x in range(0, 2)]
        self.mm_lists = self.env['mail.mass_mailing.list'].create(list_values)

        # Set Opt out
        self.env['mail.mass_mailing.list_contact_rel'].search([('contact_id', '=', self.mm_recs.ids[0]), ('list_id', '=', self.mm_lists.ids[0])]).write({
            'opt_out': True,
        })

        # Create blacklist records
        bl_values = [{'email': self.mm_recs[x].email} for x in range(3, 5)]
        self.blacklist = self.env['mail.blacklist'].create(bl_values)

        # Create mailing template
        self.mailing = self.env['mail.mass_mailing'].create({
            'name': 'Test',
            'state': 'draft',
            'body_html': 'I am Responsive body',
        })

        self.composer_template = self.env['mail.compose.message'].with_context(
            {
                'default_body': 'I am Responsive body',
                'default_subject': 'Test Subject',
                'default_model': self.mailing.mailing_model_real,
                'default_composition_mode': 'mass_mail',
                'default_mass_mailing_id': self.mailing.id
            })

    def test_mass_mail_blacklist(self):
        self.mailing.mailing_domain = [('id', 'in', [self.mm_recs[x].id for x in range(2, 5)])]

        self.mailing.send_mail()
        self.assertEqual(self.mailing.sent, 1)
        self.assertEqual(self.mailing.ignored, 2, 'Blacklist ignored email number incorrect, should be equal to 2')

    def test_mass_mail_simple_opt_out(self):
        """If a contact is opted out on list A,
           If a mailing is send to lists A, the contact should not receive the mail."""
        self.mailing.contact_list_ids = [self.mm_lists[0].id]
        self.mailing.send_mail(res_ids=self.env['mail.mass_mailing.contact'].search([('list_ids', 'in', [l.id for l in self.mailing.contact_list_ids])]).ids)

        self.assertEqual(self.mailing.sent, 1)
        self.assertEqual(self.mailing.ignored, 1, 'Opt_out ignored email number incorrect, should be equal to 1')

    def test_mass_mail_multi_opt_out(self):
        """If a contact is opted out on list A and opted in on list B,
           If a mailing is send to lists A and B, the contact should receive the mail."""
        self.mailing.contact_list_ids = [self.mm_lists[0].id, self.mm_lists[1].id]
        self.mailing.send_mail(res_ids=self.env['mail.mass_mailing.contact'].search([('list_ids', 'in', [l.id for l in self.mailing.contact_list_ids])]).ids)

        self.assertEqual(self.mailing.sent, 2)
        self.assertEqual(self.mailing.ignored, 0, 'Opt_out ignored email number incorrect, should be equal to 0')

    def test_mass_mail_multi_users_different_opt_out(self):
        """If user X is opt_out on list A but user Y with same email address than user X is not opt_out on same list,
        send the mail anyway to the opt-in contact. Ignore (as normal behaviour) opted-out contact."""
        # create mailing contact record with same email
        mm_rec_duplicated = self.mm_recs.create({'name': self.mm_recs[0].name, 'email': self.mm_recs[0].email})
        self.mm_lists[0].contact_ids = [(4, c.id) for c in self.mm_lists[0].contact_ids | mm_rec_duplicated]
        self.mailing.contact_list_ids = [self.mm_lists[0].id, self.mm_lists[1].id]
        self.mailing.send_mail(res_ids=self.env['mail.mass_mailing.contact'].search([('list_ids', 'in', [l.id for l in self.mailing.contact_list_ids])]).ids)

        self.assertEqual(self.mailing.sent, 2)
        self.assertEqual(self.mailing.ignored, 1, 'Opt_out ignored email number incorrect, should be equal to 1.')

    def test_mass_mail_on_res_partner(self):
        self.mailing.mailing_model_id = self.env['ir.model']._get('res.partner').id
        self.mailing.mailing_domain = [('id', 'in', self.mm_partners.ids)]

        self.mailing.send_mail()
        self.assertEqual(self.mailing.sent, 1)
        self.assertEqual(self.mailing.ignored, 2, 'Blacklisted ignored email number incorrect, should be equal to 2')

    def test_mass_mail_on_crm_leads(self):
        self.contact_values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(2, 5)]
        self.mm_recs = self.env['crm.lead'].create(self.contact_values)

        self.mailing.mailing_model_id = self.env['ir.model']._get('crm.lead').id
        self.mailing.mailing_domain = [('id', 'in', self.mm_recs.ids)]

        self.mailing.send_mail()
        self.assertEqual(self.mailing.sent, 1)
        self.assertEqual(self.mailing.ignored, 2, 'Blacklisted ignored email number should be equal to 2')

    def test_channel_blacklisted_recipients(self):
        self.test_channel = self.env['mail.channel'].create({
            'name': 'Test',
            'description': 'Description',
            'alias_name': 'test',
            'public': 'public',
        })

        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'schlouby.fr')
        self.test_channel.write({'email_send': True})
        self._join_channel(self.test_channel, self.mm_partners)
        self.test_channel.message_post(body="Test", message_type='comment', subtype='mt_comment')

        self.assertEqual(len(self._mails), 1, 'Number of mail incorrect. Should be equal to 1.')
        for email in self._mails:
            self.assertEqual(
                set(email['email_to']),
                set([formataddr((self.mm_partners[0].name, self.mm_partners[0].email))]),
                'email_to incorrect. Should be equal to "%s"' % (
                    formataddr((self.mm_partners[0].name, self.mm_partners[0].email))))

    def test_mail_bounced_auto_blacklist(self):
        # create bounced history
        mail_stat_values = [{
            'model': 'mail.mass_mailing.contact',
            'res_id': self.mm_recs[2].id,
            'bounced': datetime.datetime.now() - datetime.timedelta(weeks=x),
            'email': self.mm_recs[2].email
        } for x in range(2, 7)]
        self.mm_stats = self.env['mail.mail.statistics'].create(mail_stat_values)
        # If message bounce < 5, should not auto blacklist the recipient,
        # even if statistics has 5 bounced without last 3 month
        # (-> If bounce reset, we keep stat but we start again a new cycle of waiting for 5 bounced.)
        for x in range(0, 4):
            self.mm_recs[2].message_receive_bounce(self.mm_recs[2].email, self.mm_recs[2])

        # Send 1st mail - should be send
        self.mailing.mailing_domain = [('id', '=', self.mm_recs[2].id)]
        self.mailing.send_mail()
        self.assertEqual(self.mailing.sent, 1)
        self.assertEqual(self.mailing.ignored, 0, 'Blacklist ignored email number incorrect, should be equal to 1')
        # check blacklist
        blacklist_record = self.env['mail.blacklist'].search([('email', '=', self.mm_recs[2].email)])
        self.assertEqual(len(blacklist_record), 0, 'The email %s must not be blacklisted yet' % self.mm_recs[2].email)

        # Send 2nd mail after bounce
        # Simulate Bounce
        self.mm_recs[2].message_receive_bounce(self.mm_recs[2].email, self.mm_recs[2])
        self.mailing2 = self.env['mail.mass_mailing'].create({
            'name': 'Test',
            'state': 'draft',
            'mailing_domain': [('id', '=', self.mm_recs[2].id)]
        })
        self.mailing2.send_mail()
        self.assertEqual(self.mailing2.sent, 0)
        self.assertEqual(self.mailing2.ignored, 1, 'Blacklist ignored email number incorrect, should be equal to 1')
        # check blacklist
        blacklist_record = self.env['mail.blacklist'].search([('email', '=', self.mm_recs[2].email)])
        self.assertEqual(len(blacklist_record), 1, 'The email %s must be blacklisted' % self.mm_recs[2].email)

        # Send 3rd mail after received mail and client asked to unblacklist
        # TODO : send mail from self.mm_recs[2] address and not call directly reset_bounce
        self.mm_recs[2]._reset_message_bounce(self.mm_recs[2].email)
        self.env['mail.blacklist'].remove(self.mm_recs[2].email)
        self.mailing3 = self.env['mail.mass_mailing'].create({
            'name': 'Test',
            'state': 'draft',
            'mailing_domain': [('id', '=', self.mm_recs[2].id)]
        })
        self.mailing3.send_mail()
        self.assertEqual(self.mailing2.sent, 1)
        self.assertEqual(self.mailing2.ignored, 0, 'Blacklist ignored email number incorrect, should be equal to 0')
        # check blacklist
        blacklist_record = self.env['mail.blacklist'].search([('email', '=', self.mm_recs[2].email)])
        self.assertEqual(len(blacklist_record), 0, 'The email %s must not be blacklisted anymore' % self.mm_recs[2].email)
