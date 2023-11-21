# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests.common import Form, users
from odoo.tests import tagged


# samples use effective TLDs from the Mozilla public suffix
# list at http://publicsuffix.org
SAMPLES = [
    ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('ryu+giga-Sushi@aizubange.fukushima.jp', '', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
    ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
    (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
    ('Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@CHIRURGIENS-dentistes.fr'),
    ('Raoul megaraoul@chirurgiens-dentistes.fr', 'Raoul', 'megaraoul@chirurgiens-dentistes.fr'),
    ('"Patrick Da Beast Poilvache" <PATRICK@example.com>', 'Patrick Poilvache', 'patrick@example.com'),
    ('Patrick Caché <patrick@EXAMPLE.COM>', 'Patrick Poilvache', 'patrick@example.com'),
    ('Patrick Caché <2patrick@EXAMPLE.COM>', 'Patrick Caché', '2patrick@example.com'),

]

@tagged('res_partner')
class TestPartner(MailCommon):

    def _check_find_or_create(self, test_string, expected_name, expected_email, expected_email_normalized=False, check_partner=False, should_create=False):
        expected_email_normalized = expected_email_normalized or expected_email
        partner = self.env['res.partner'].find_or_create(test_string)
        if should_create and check_partner:
            self.assertTrue(partner.id > check_partner.id, 'find_or_create failed - should have found existing')
        elif check_partner:
            self.assertEqual(partner, check_partner, 'find_or_create failed - should have found existing')
        self.assertEqual(partner.name, expected_name)
        self.assertEqual(partner.email or '', expected_email)
        self.assertEqual(partner.email_normalized or '', expected_email_normalized)
        return partner

    def test_res_partner_find_or_create(self):
        Partner = self.env['res.partner']

        partner = Partner.browse(Partner.name_create(SAMPLES[0][0])[0])
        self._check_find_or_create(
            SAMPLES[0][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        partner_2 = Partner.browse(Partner.name_create('sarah.john@connor.com')[0])
        found_2 = self._check_find_or_create(
            'john@connor.com', 'john@connor.com', 'john@connor.com',
            check_partner=partner_2, should_create=True
        )

        new = self._check_find_or_create(
            SAMPLES[1][0], SAMPLES[1][2].lower(), SAMPLES[1][2].lower(),
            check_partner=found_2, should_create=True
        )

        new2 = self._check_find_or_create(
            SAMPLES[2][0], SAMPLES[2][1], SAMPLES[2][2],
            check_partner=new, should_create=True
        )

        self._check_find_or_create(
            SAMPLES[3][0], SAMPLES[3][1], SAMPLES[3][2],
            check_partner=new2, should_create=True
        )

        new4 = self._check_find_or_create(
            SAMPLES[4][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        self._check_find_or_create(
            SAMPLES[5][0], SAMPLES[5][1], SAMPLES[5][2],
            check_partner=new4, should_create=True
        )

        existing = Partner.create({
            'name': SAMPLES[6][1],
            'email': SAMPLES[6][0],
        })
        self.assertEqual(existing.name, SAMPLES[6][1])
        self.assertEqual(existing.email, SAMPLES[6][0])
        self.assertEqual(existing.email_normalized, SAMPLES[6][2])

        new6 = self._check_find_or_create(
            SAMPLES[7][0], SAMPLES[6][1], SAMPLES[6][0],
            expected_email_normalized=SAMPLES[6][2],
            check_partner=existing, should_create=False
        )

        self._check_find_or_create(
            SAMPLES[8][0], SAMPLES[8][1], SAMPLES[8][2],
            check_partner=new6, should_create=True
        )

        with self.assertRaises(ValueError):
            self.env['res.partner'].find_or_create("Raoul chirurgiens-dentistes.fr", assert_valid_email=True)

    def test_res_partner_log_portal_group(self):
        Users = self.env['res.users']
        subtype_note = self.env.ref('mail.mt_note')
        group_portal, group_user = self.env.ref('base.group_portal'), self.env.ref('base.group_user')

        # check at update
        new_user = Users.create({
            'email': 'micheline@test.example.com',
            'login': 'michmich',
            'name': 'Micheline Employee',
        })
        self.assertEqual(len(new_user.message_ids), 1, 'Should contain Contact created log message')
        new_msg = new_user.message_ids
        self.assertNotIn('Portal Access Granted', new_msg.body)
        self.assertIn('Contact created', new_msg.body)

        new_user.write({'groups_id': [(4, group_portal.id), (3, group_user.id)]})
        new_msg = new_user.message_ids[0]
        self.assertIn('Portal Access Granted', new_msg.body)
        self.assertEqual(new_msg.subtype_id, subtype_note)

        # check at create
        new_user = Users.create({
            'email': 'micheline.2@test.example.com',
            'groups_id': [(4, group_portal.id)],
            'login': 'michmich.2',
            'name': 'Micheline Portal',
        })
        self.assertEqual(len(new_user.message_ids), 2, 'Should contain Contact created + Portal access log messages')
        new_msg = new_user.message_ids[0]
        self.assertIn('Portal Access Granted', new_msg.body)
        self.assertEqual(new_msg.subtype_id, subtype_note)

    def test_res_partner_get_mention_suggestions_priority(self):
        name = uuid4()  # unique name to avoid conflict with already existing users
        self.env['res.partner'].create([{'name': f'{name}-{i}-not-user'} for i in range(0, 2)])
        for i in range(0, 2):
            mail_new_test_user(self.env, login=f'{name}-{i}-portal-user', groups='base.group_portal')
            mail_new_test_user(self.env, login=f'{name}-{i}-internal-user', groups='base.group_user')
        partners_format = self.env['res.partner'].get_mention_suggestions(name, limit=5)
        self.assertEqual(len(partners_format), 5, "should have found limit (5) partners")
        self.assertEqual(list(map(lambda p: p['is_internal_user'], partners_format)), [True, True, False, False, False], "should return internal users in priority")
        self.assertEqual(list(map(lambda p: bool(p['user_id']), partners_format)), [True, True, True, True, False], "should return partners without users last")

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
