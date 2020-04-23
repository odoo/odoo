# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMassMailing(TestMassMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailing, cls).setUpClass()

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_blacklist(self):
        mailing = self.mailing_bl.with_user(self.env.user)
        recipients = self._create_test_blacklist_records(count=5)

        # blacklist records 3 and 4
        self.env['mail.blacklist'].create({'email': recipients[3].email_normalized})
        self.env['mail.blacklist'].create({'email': recipients[4].email_normalized})

        mailing.write({'mailing_domain': [('id', 'in', recipients.ids)]})
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com'},
             {'email': 'test.record.01@test.example.com'},
             {'email': 'test.record.02@test.example.com'},
             {'email': 'test.record.03@test.example.com', 'state': 'ignored'},
             {'email': 'test.record.04@test.example.com', 'state': 'ignored'}],
            mailing, recipients, check_mail=True
        )
        self.assertEqual(mailing.ignored, 2)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_w_opt_out(self):
        mailing = self.mailing_bl.with_user(self.env.user)
        recipients = self._create_test_blacklist_records(model='mailing.test.optout', count=5)

        # optout records 0 and 1
        (recipients[0] | recipients[1]).write({'opt_out': True})
        # blacklist records 4
        self.env['mail.blacklist'].create({'email': recipients[4].email_normalized})

        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mailing.test.optout'),
            'mailing_domain': [('id', 'in', recipients.ids)]
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test.record.00@test.example.com', 'state': 'ignored'},
             {'email': 'test.record.01@test.example.com', 'state': 'ignored'},
             {'email': 'test.record.02@test.example.com'},
             {'email': 'test.record.03@test.example.com'},
             {'email': 'test.record.04@test.example.com', 'state': 'ignored'}],
            mailing, recipients, check_mail=True
        )
        self.assertEqual(mailing.ignored, 3)

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mailing_mailing_list_optout(self):
        """ Test mailing list model specific optout behavior """
        mailing_contact_1 = self.env['mailing.contact'].create({'name': 'test 1A', 'email': 'test@test.example.com'})
        mailing_contact_2 = self.env['mailing.contact'].create({'name': 'test 1B', 'email': 'test@test.example.com'})
        mailing_contact_3 = self.env['mailing.contact'].create({'name': 'test 3', 'email': 'test3@test.example.com'})
        mailing_contact_4 = self.env['mailing.contact'].create({'name': 'test 4', 'email': 'test4@test.example.com'})
        mailing_contact_5 = self.env['mailing.contact'].create({'name': 'test 5', 'email': 'test5@test.example.com'})

        # create mailing list record
        mailing_list_1 = self.env['mailing.list'].create({
            'name': 'A',
            'contact_ids': [
                (4, mailing_contact_1.id),
                (4, mailing_contact_2.id),
                (4, mailing_contact_3.id),
                (4, mailing_contact_5.id),
            ]
        })
        mailing_list_2 = self.env['mailing.list'].create({
            'name': 'B',
            'contact_ids': [
                (4, mailing_contact_3.id),
                (4, mailing_contact_4.id),
            ]
        })
        # contact_1 is optout but same email is not optout from the same list
        # contact 3 is optout in list 1 but not in list 2
        # contact 5 is optout
        Sub = self.env['mailing.contact.subscription']
        Sub.search([('contact_id', '=', mailing_contact_1.id), ('list_id', '=', mailing_list_1.id)]).write({'opt_out': True})
        Sub.search([('contact_id', '=', mailing_contact_3.id), ('list_id', '=', mailing_list_1.id)]).write({'opt_out': True})
        Sub.search([('contact_id', '=', mailing_contact_5.id), ('list_id', '=', mailing_list_1.id)]).write({'opt_out': True})

        # create mass mailing record
        mailing = self.env['mailing.mailing'].create({
            'name': 'SourceName',
            'subject': 'MailingSubject',
            'body_html': '<p>Hello ${object.name}</p>',
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(4, ml.id) for ml in mailing_list_1 | mailing_list_2],
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        self.assertMailTraces(
            [{'email': 'test@test.example.com', 'state': 'ignored'},
             {'email': 'test@test.example.com', 'state': 'sent'},
             {'email': 'test3@test.example.com'},
             {'email': 'test4@test.example.com'},
             {'email': 'test5@test.example.com', 'state': 'ignored'}],
            mailing,
            mailing_contact_1 | mailing_contact_2 | mailing_contact_3 | mailing_contact_4 | mailing_contact_5,
            check_mail=True
        )
        self.assertEqual(mailing.ignored, 2)
