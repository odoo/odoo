# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls

from odoo.addons.test_mass_mailing.tests.common import TestMailCommon
from odoo.tests.common import TransactionCase, users
from odoo.tools import mute_logger


class TestMassMail(TestMailCommon):

    def setUp(self):
        """ In this setup we prepare 20 blacklist entries. We therefore add
        20 recipients compared to first test in order to have comparable results. """
        super(TestMassMail, self).setUp()
        values = [{
            'name': 'Recipient %s' % x,
            'email_from': 'Recipient <rec.%s@example.com>' % x,
        } for x in range(0, 6)]
        self.mm_recs = self.env['mass.mail.test.bl'].create(values)

        self.env['mail.blacklist'].create({
            'email': 'rec.2@example.com'
        })

        self.test_medium = self.env['utm.medium'].create({'name': 'TestMedium'})

    @users('marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail', 'odoo.models.unlink')
    def test_link_tracker(self):
        _url = 'https://www.example.com/foo/bar?baz=qux'
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestMailing',
            'subject': 'Test',
            'medium_id': self.test_medium.id,
            'body_html': '<p>Hello <a role="button" href="%s">${object.name}</a><a role="button" href="/unsubscribe_from_list">Unsubscribe</a></p>' % _url,
            'reply_to_mode': 'email',
            'mailing_model_id': self.ref('test_mass_mailing.model_mass_mail_test_bl'),
            'mailing_domain': [('id', 'in', self.mm_recs.ids)],
        })

        mailing.action_send_mail()

        # basic test emails are sent
        self.assertEqual(mailing.sent, 5)
        self.assertEqual(mailing.delivered, 5)

        # link trackers
        links = self.env['link.tracker'].sudo().search([('mass_mailing_id', '=', mailing.id)])
        self.assertEqual(len(links), 1)
        self.assertEqual(links.mapped('url'), [_url])
        # check UTMS are correctly set on redirect URL
        redirect_url = urls.url_parse(links.redirected_url)
        redirect_params = redirect_url.decode_query().to_dict(flat=True)
        self.assertEqual(redirect_url.scheme, 'https')
        self.assertEqual(redirect_url.decode_netloc(), 'www.example.com')
        self.assertEqual(redirect_url.path, '/foo/bar')
        self.assertEqual(redirect_params, {
            'utm_source': mailing.name,
            'utm_medium': self.test_medium.name,
            'baz': 'qux',
        })


class TestAccessRights(TransactionCase):

    def test_01_mass_mail_blacklist(self):
        mass_mailing_contacts = self.env['mailing.contact']
        mass_mailing = self.env['mailing.mailing']
        mail_blacklist = self.env['mail.blacklist']

        # create mailing contact record
        self.mailing_contact_1 = mass_mailing_contacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        self.mailing_contact_2 = mass_mailing_contacts.create({'name': 'test email 2', 'email': 'test2@email.com'})
        self.mailing_contact_3 = mass_mailing_contacts.create({'name': 'test email 3', 'email': 'test3@email.com'})
        self.mailing_contact_4 = mass_mailing_contacts.create({'name': 'test email 4', 'email': 'test4@email.com'})
        self.mailing_contact_5 = mass_mailing_contacts.create({'name': 'test email 5', 'email': 'test5@email.com'})

        # create blacklist record
        mail_blacklist.create({'email': self.mailing_contact_3.email})
        mail_blacklist.create({'email': self.mailing_contact_4.email})

        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'test',
            'subject': 'Blacklisted',
            'mailing_domain': [('id', 'in',
                                [self.mailing_contact_1.id, self.mailing_contact_2.id, self.mailing_contact_3.id,
                                 self.mailing_contact_4.id, self.mailing_contact_5.id])],
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.action_put_in_queue()
        res_ids = self.mass_mailing._get_remaining_recipients()
        composer_values = {
            'body': self.mass_mailing.convert_links()[self.mass_mailing.id],
            'subject': self.mass_mailing.name,
            'model': self.mass_mailing.mailing_model_real,
            'email_from': self.mass_mailing.email_from,
            'composition_mode': 'mass_mail',
            'mass_mailing_id': self.mass_mailing.id,
            'mailing_list_ids': [(4, l.id) for l in self.mass_mailing.contact_list_ids],
        }
        composer = self.env['mail.compose.message'].with_context(active_ids=res_ids,
                                                                 mass_mailing_seen_list=self.mass_mailing._get_seen_list()).create(
            composer_values)
        composer.send_mail()
        self.assertEqual(self.mass_mailing.canceled, 2,
                         'blacklist canceled email number incorrect, should be equals to 2')

    def test_02_mass_mail_simple_opt_out(self):
        mass_mailing_contacts = self.env['mailing.contact']
        mass_mailing_lists = self.env['mailing.list']
        mass_mailing_optout = self.env['mailing.contact.subscription']
        mass_mailing = self.env['mailing.mailing']

        # create mailing contact record
        mailing_contact_1 = mass_mailing_contacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        mailing_contact_2 = mass_mailing_contacts.create({'name': 'test email 2', 'email': 'test2@email.com'})

        # create mailing list record
        mailing_list_1 = mass_mailing_lists.create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })

        # Set Opt out
        mass_mailing_optout.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({
            'opt_out': True,
        })

        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'One',
            'subject': 'One',
            'mailing_model_id': self.env['ir.model']._get('mailing.contact').id,
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.contact_list_ids = [mailing_list_1.id]
        self.mass_mailing.action_put_in_queue()
        composer_values = {
            'body': self.mass_mailing.convert_links()[self.mass_mailing.id],
            'subject': self.mass_mailing.name,
            'model': self.mass_mailing.mailing_model_real,
            'email_from': self.mass_mailing.email_from,
            'composition_mode': 'mass_mail',
            'mass_mailing_id': self.mass_mailing.id,
            'mailing_list_ids': [(4, l.id) for l in self.mass_mailing.contact_list_ids],
        }
        composer = self.env['mail.compose.message'].with_context(
            active_ids=[mailing_contact_1.id, mailing_contact_2.id],
            mass_mailing_seen_list=self.mass_mailing._get_seen_list(),
            mass_mailing_opt_out_list=self.mass_mailing._get_opt_out_list()).create(composer_values)
        composer.send_mail()
        self.assertEqual(self.mass_mailing.canceled, 1,
                         'Opt Out canceled email number incorrect, should be equals to 1')

    def test_03_mass_mail_multi_opt_out(self):
        mass_mailing_contacts = self.env['mailing.contact']
        mass_mailing_lists = self.env['mailing.list']
        mass_mailing_optout = self.env['mailing.contact.subscription']
        mass_mailing = self.env['mailing.mailing']

        # create mailing contact record
        mailing_contact_1 = mass_mailing_contacts.create({'name': 'test email 1', 'email': 'test1@email.com'})
        mailing_contact_2 = mass_mailing_contacts.create({'name': 'test email 2', 'email': 'test2@email.com'})

        # create mailing list record
        mailing_list_1 = mass_mailing_lists.create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })
        mailing_list_2 = mass_mailing_lists.create({
            'name': 'B',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })

        # Set Opt out
        mass_mailing_optout.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({
            'opt_out': True,
        })

        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'One',
            'subject': 'One',
            'mailing_model_id': self.env['ir.model']._get('mailing.contact').id,
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.contact_list_ids = [mailing_list_1.id, mailing_list_2.id]
        self.mass_mailing.action_put_in_queue()
        composer_values = {
            'body': self.mass_mailing.convert_links()[self.mass_mailing.id],
            'subject': self.mass_mailing.name,
            'model': self.mass_mailing.mailing_model_real,
            'email_from': self.mass_mailing.email_from,
            'composition_mode': 'mass_mail',
            'mass_mailing_id': self.mass_mailing.id,
            'mailing_list_ids': [(4, l.id) for l in self.mass_mailing.contact_list_ids],
        }
        composer = self.env['mail.compose.message'].with_context(
            active_ids=[mailing_contact_1.id, mailing_contact_2.id],
            mass_mailing_seen_list=self.mass_mailing._get_seen_list(),
            mass_mailing_opt_out_list=self.mass_mailing._get_opt_out_list()).create(composer_values)
        composer.send_mail()
        # if user is opt_out on One list but not on another, send the mail anyway
        self.assertEqual(self.mass_mailing.canceled, 0,
                         'Opt Out canceled email number incorrect, should be equals to 0')

    def test_04_mass_mail_multi_users_different_opt_out(self):
        mass_mailing_contacts = self.env['mailing.contact']
        mass_mailing_lists = self.env['mailing.list']
        mass_mailing_optout = self.env['mailing.contact.subscription']
        mass_mailing = self.env['mailing.mailing']

        # create mailing contact record
        mailing_contact_1 = mass_mailing_contacts.create({'name': 'test email (A)', 'email': 'test@email.com'})
        mailing_contact_2 = mass_mailing_contacts.create({'name': 'test email (B)', 'email': 'test@email.com'})

        # create mailing list record
        mailing_list_1 = mass_mailing_lists.create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id)
            ]
        })

        # Set Opt out
        mass_mailing_optout.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({
            'opt_out': True,
        })

        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'One',
            'subject': 'One',
            'mailing_model_id': self.env['ir.model']._get('mailing.contact').id,
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.contact_list_ids = [mailing_list_1.id]
        self.mass_mailing.action_put_in_queue()
        composer_values = {
            'body': self.mass_mailing.convert_links()[self.mass_mailing.id],
            'subject': self.mass_mailing.name,
            'model': self.mass_mailing.mailing_model_real,
            'email_from': self.mass_mailing.email_from,
            'composition_mode': 'mass_mail',
            'mass_mailing_id': self.mass_mailing.id,
            'mailing_list_ids': [(4, l.id) for l in self.mass_mailing.contact_list_ids],
        }
        composer = self.env['mail.compose.message'].with_context(
            active_ids=[mailing_contact_1.id, mailing_contact_2.id],
            mass_mailing_seen_list=self.mass_mailing._get_seen_list(),
            mass_mailing_opt_out_list=self.mass_mailing._get_opt_out_list()).create(composer_values)
        composer.send_mail()
        # if user A is opt_out on One list but user B  is not opt_out on same list,
        # send the mail anyway to the opt-in contact. Ignore (as normal behaviour) opted-out contact.
        self.assertEqual(self.mass_mailing.canceled, 1,
                         'Opt Out canceled email number incorrect, should be equals to 1')


class TestOnResPartner(TransactionCase):

    def test_mass_mail_on_res_partner(self):
        partners = self.env['res.partner']
        mass_mailing = self.env['mailing.mailing']

        # create mailing contact record
        partner_a = partners.create({
            'name': 'test email 1',
            'email': 'test1@email.com',
        })
        partner_b = partners.create({
            'name': 'test email 2',
            'email': 'test2@email.com',
        })

        # Set Blacklist
        self.blacklist_contact_entry = self.env['mail.blacklist'].create({
            'email': 'Test2@email.com',
        })

        # create mass mailing record
        self.mass_mailing = mass_mailing.create({
            'name': 'One',
            'subject': 'One',
            'mailing_domain': [('id', 'in', [partner_a.id, partner_b.id])],
            'body_html': 'This is mass mail marketing demo'})
        self.mass_mailing.mailing_model_real = 'res.partner'
        self.mass_mailing.action_put_in_queue()
        res_ids = self.mass_mailing._get_remaining_recipients()
        composer_values = {
            'body': self.mass_mailing.convert_links()[self.mass_mailing.id],
            'subject': self.mass_mailing.name,
            'model': self.mass_mailing.mailing_model_real,
            'email_from': self.mass_mailing.email_from,
            'composition_mode': 'mass_mail',
            'mass_mailing_id': self.mass_mailing.id,
            'mailing_list_ids': [(4, l.id) for l in self.mass_mailing.contact_list_ids],
        }
        composer = self.env['mail.compose.message'].with_context(
            active_ids=res_ids,
            mass_mailing_seen_list=self.mass_mailing._get_seen_list()).create(composer_values)
        composer.send_mail()
        # if user is opt_out on One list but not on another, send the mail anyway
        self.assertEqual(self.mass_mailing.canceled, 1,
                         'Blacklisted canceled email number incorrect, should be equals to 1')
