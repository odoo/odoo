# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase


class TestMassMailingBlaclist(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mailing_list_obj = cls.env['mail.mass_mailing.list']
        contact_obj = cls.env['mail.mass_mailing.contact']
        cls.list_A = mailing_list_obj.create({
            'name': 'A',
        })
        cls.list_B = mailing_list_obj.create({
            'name': 'B',
        })
        cls.contact_A_A = contact_obj.create({
            'email': 'a@a.com',
            'list_ids': [(6, 0, cls.list_A.ids)],
        })
        cls.contact_A_B = contact_obj.create({
            'email': 'b@b.com',
            'list_ids': [(6, 0, cls.list_A.ids)],
        })
        cls.contact_A_C = contact_obj.create({
            'email': 'c@c.com',
            'list_ids': [(6, 0, cls.list_A.ids)],
        })
        cls.contact_B_A = contact_obj.create({
            'email': 'a@a.com',
            'list_ids': [(6, 0, cls.list_B.ids)],
        })
        cls.contact_B_B = contact_obj.create({
            'email': 'b@b.com',
            'list_ids': [(6, 0, cls.list_B.ids)],
        })
        cls.contact_B_C = contact_obj.create({
            'email': 'c@c.com',
            'list_ids': [(6, 0, cls.list_B.ids)],
        })
        cls.mass_mailing = cls.env['mail.mass_mailing'].create({
            'name': 'Test Mass Mailing Blacklist',
            'email_from': 'Administrator <admin@yourcompany.example.com>',
            "reply_to_mode": 'email',
            "reply_to": 'Administrator <admin@yourcompany.example.com>',
            "mailing_model_id": cls.env.ref(
                'mass_mailing.model_mail_mass_mailing_list').id,
            "mailing_domain": "[('list_ids', 'in', [%d])]" % cls.list_A.id,
            "contact_list_ids": [(6, 0, cls.list_A.ids)],
            "mass_mailing_campaign_id": False,
            "body_html": '',
        })
        # We unsubscribe email a@a.com from list_A. It will remain
        # subscribed to list_B
        cls.contact_A_A.opt_out = True

    def test_mass_mailing_blacklist(self):
        # a@a.com is unsubscribed from list_A, so only two emails should be
        # sent and the third one will be in exception
        self.mass_mailing.put_in_queue()
        self.mass_mailing._process_mass_mailing_queue()
        self.assertEqual(self.mass_mailing.sent, 2)
        stats = self.mass_mailing.statistics_ids
        self.assertEqual(len(stats), 3)
        self.assertEqual(len(stats.filtered('exception')), 1)

    def test_mass_mailing_no_blacklist(self):
        # a@a.com is unsubscribed from list_A, but not in list_B so all
        # the emails should be sent
        self.mass_mailing.contact_list_ids = self.list_B
        self.mass_mailing._onchange_model_and_list()
        self.mass_mailing.put_in_queue()
        self.mass_mailing._process_mass_mailing_queue()
        self.assertEqual(self.mass_mailing.sent, 3)
        stats = self.mass_mailing.statistics_ids
        self.assertEqual(len(stats), 3)
        self.assertEqual(len(stats.filtered('exception')), 0)

    def test_mass_mailing_no_blacklist_mixed(self):
        # a@a.com is unsubscribed from list_A, but not in list_B so all
        # the emails should be sent although list_A is in the mailing as well
        self.mass_mailing.contact_list_ids |= self.list_B
        self.mass_mailing._onchange_model_and_list()
        self.mass_mailing.put_in_queue()
        self.mass_mailing._process_mass_mailing_queue()
        self.assertEqual(self.mass_mailing.sent, 3)
