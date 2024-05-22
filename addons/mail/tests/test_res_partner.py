# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import Form, users
from odoo.tests import tagged


@tagged('res_partner')
class TestPartner(MailCommon):

    def test_res_partner_find_or_create(self):
        Partner = self.env['res.partner']

        existing = Partner.create({
            'name': 'Patrick Poilvache',
            'email': '"Patrick Da Beast Poilvache" <PATRICK@example.com>',
        })
        self.assertEqual(existing.name, 'Patrick Poilvache')
        self.assertEqual(existing.email, '"Patrick Da Beast Poilvache" <PATRICK@example.com>')
        self.assertEqual(existing.email_normalized, 'patrick@example.com')

        new = Partner.find_or_create('Patrick Caché <patrick@EXAMPLE.COM>')
        self.assertEqual(new, existing)

        new2 = Partner.find_or_create('Patrick Caché <2patrick@EXAMPLE.COM>')
        self.assertTrue(new2.id > new.id)
        self.assertEqual(new2.name, 'Patrick Caché')
        self.assertEqual(new2.email, '2patrick@example.com')
        self.assertEqual(new2.email_normalized, '2patrick@example.com')

    @users('admin')
    def test_res_partner_find_or_create_email(self):
        """ Test 'find_or_create' tool used in mail, notably when linking emails
        found in recipients to partners when sending emails using the mail
        composer. """
        partners = self.env['res.partner'].create([
            {
                'email': 'classic.format@test.example.com',
                'name': 'Classic Format',
            },
            {
                'email': '"FindMe Format" <find.me.format@test.example.com>',
                'name': 'FindMe Format',
            }, {
                'email': 'find.me.multi.1@test.example.com, "FindMe Multi" <find.me.multi.2@test.example.com>',
                'name': 'FindMe Multi',
            },
        ])
        # check data used for finding / searching
        self.assertEqual(
            partners.mapped('email_formatted'),
            ['"Classic Format" <classic.format@test.example.com>',
             '"FindMe Format" <find.me.format@test.example.com>',
             '"FindMe Multi" <find.me.multi.1@test.example.com,find.me.multi.2@test.example.com>']
        )
        # when having multi emails, first found one is taken as normalized email
        self.assertEqual(
            partners.mapped('email_normalized'),
            ['classic.format@test.example.com', 'find.me.format@test.example.com',
             'find.me.multi.1@test.example.com']
        )

        # classic find or create: use normalized email to compare records
        for email in ('CLASSIC.FORMAT@TEST.EXAMPLE.COM', '"Another Name" <classic.format@test.example.com>'):
            with self.subTest(email=email):
                self.assertEqual(self.env['res.partner'].find_or_create(email), partners[0])
        # find on encapsulated email: comparison of normalized should work
        for email in ('FIND.ME.FORMAT@TEST.EXAMPLE.COM', '"Different Format" <find.me.format@test.example.com>'):
            with self.subTest(email=email):
                self.assertEqual(self.env['res.partner'].find_or_create(email), partners[1])
        # multi-emails -> no normalized email -> fails each time, create new partner (FIXME)
        for email_input, match_partner in [
            ('find.me.multi.1@test.example.com', partners[2]),
            ('find.me.multi.2@test.example.com', self.env['res.partner']),
        ]:
            with self.subTest(email_input=email_input):
                partner = self.env['res.partner'].find_or_create(email_input)
                # either matching existing, either new partner
                if match_partner:
                    self.assertEqual(partner, match_partner)
                else:
                    self.assertNotIn(partner, partners)
                    self.assertEqual(partner.email, email_input)
                partner.unlink()  # do not mess with subsequent tests

        # now input is multi email -> '_parse_partner_name' used in 'find_or_create'
        # before trying to normalize is quite tolerant, allowing positive checks
        for email_input, match_partner, exp_email_partner in [
            ('classic.format@test.example.com,another.email@test.example.com',
              partners[0], 'classic.format@test.example.com'),  # first found email matches existing
            ('another.email@test.example.com,classic.format@test.example.com',
             self.env['res.partner'], 'another.email@test.example.com'),  # first found email does not match
            ('find.me.multi.1@test.example.com,find.me.multi.2@test.example.com',
             self.env['res.partner'], 'find.me.multi.1@test.example.com'),
        ]:
            with self.subTest(email_input=email_input):
                partner = self.env['res.partner'].find_or_create(email_input)
                # either matching existing, either new partner
                if match_partner:
                    self.assertEqual(partner, match_partner)
                else:
                    self.assertNotIn(partner, partners)
                self.assertEqual(partner.email, exp_email_partner)
                if partner not in partners:
                    partner.unlink()  # do not mess with subsequent tests

    @users('admin')
    def test_res_partner_merge_wizards(self):
        Partner = self.env['res.partner']

        p1 = Partner.create({'name': 'Customer1', 'email': 'test1@test.example.com'})
        p1_msg_ids_init = p1.message_ids
        p2 = Partner.create({'name': 'Customer2', 'email': 'test2@test.example.com'})
        p2_msg_ids_init = p2.message_ids
        p3 = Partner.create({'name': 'Other (dup email)', 'email': 'test1@test.example.com'})

        # add some mail related documents
        p1.message_subscribe(partner_ids=p3.ids)
        p1_act1 = p1.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo')
        p1_msg1 = p1.message_post(
            body='<p>Log on P1</p>',
            subtype_id=self.env.ref('mail.mt_comment').id
        )
        self.assertEqual(p1.activity_ids, p1_act1)
        self.assertEqual(p1.message_follower_ids.partner_id, self.partner_admin + p3)
        self.assertEqual(p1.message_ids, p1_msg_ids_init + p1_msg1)
        self.assertEqual(p2.activity_ids, self.env['mail.activity'])
        self.assertEqual(p2.message_follower_ids.partner_id, self.partner_admin)
        self.assertEqual(p2.message_ids, p2_msg_ids_init)

        MergeForm = Form(self.env['base.partner.merge.automatic.wizard'].with_context(
            active_model='res.partner',
            active_ids=(p1 + p2).ids
        ))
        self.assertEqual(MergeForm.partner_ids[:], p1 + p2)
        self.assertEqual(MergeForm.dst_partner_id, p2)
        merge_form = MergeForm.save()
        merge_form.action_merge()

        # check destination and removal
        self.assertFalse(p1.exists())
        self.assertTrue(p2.exists())
        # check mail documents have been moved
        self.assertEqual(p2.activity_ids, p1_act1)
        # TDE note: currently not working as soon as there is a single partner duplicated -> should be improved
        # self.assertEqual(p2.message_follower_ids.partner_id, self.partner_admin + p3)
        all_msg = p2_msg_ids_init + p1_msg_ids_init + p1_msg1
        self.assertEqual(len(p2.message_ids), len(all_msg) + 1, 'Should have original messages + a log')
        self.assertTrue(all(msg in p2.message_ids for msg in all_msg))
