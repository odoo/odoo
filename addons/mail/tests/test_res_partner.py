# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from unittest.mock import patch
from uuid import uuid4

from odoo import tools
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests.common import Form, tagged, users
from odoo.addons.base.models.res_partner import Partner

# samples use effective TLDs from the Mozilla public suffix
# list at http://publicsuffix.org
SAMPLES = [
    ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
    ('ryu+giga-Sushi@aizubange.fukushima.jp', 'ryu+giga-sushi@aizubange.fukushima.jp', 'ryu+giga-Sushi@aizubange.fukushima.jp'),
    ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
    (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
    ('Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@CHIRURGIENS-dentistes.fr'),
    ('Raoul megaraoul@chirurgiens-dentistes.fr', 'Raoul', 'megaraoul@chirurgiens-dentistes.fr'),
    ('"Patrick Da Beast Poilvache" <PATRICK@example.com>', 'Patrick Da Beast Poilvache', 'patrick@example.com'),
    ('Patrick Caché <patrick@EXAMPLE.COM>', 'Patrick Da Beast Poilvache', 'patrick@example.com'),
    ('Patrick Caché <patrick.2@EXAMPLE.COM>', 'Patrick Caché', 'patrick.2@example.com'),
]


@tagged('res_partner')
class TestPartner(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._activate_multi_company()

    @contextmanager
    def mockPartnerCalls(self):
        _original_create = Partner.create
        _original_search = Partner.search
        self._new_partners = self.env['res.partner']

        def _res_partner_create(model, *args, **kwargs):
            records = _original_create(model, *args, **kwargs)
            self._new_partners += records.sudo()
            return records

        with patch.object(Partner, 'create',
                          autospec=True, side_effect=_res_partner_create) as mock_partner_create, \
             patch.object(Partner, 'search',
                          autospec=True, side_effect=_original_search) as mock_partner_search:
            self._mock_partner_create = mock_partner_create
            self._mock_partner_search = mock_partner_search
            yield

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

    def test_parse_partner_name(self):
        samples = [
            'Raoul raoul@grosbedon.fr',
            'Raoul chirurgiens-dentistes.fr',
            'invalid',
            'False',
            '',
            ' ',
            False,
            None,
        ]
        expected = [
            ('Raoul', 'raoul@grosbedon.fr'),
            ('Raoul chirurgiens-dentistes.fr', ''),
            ('invalid', ''),
            ('False', ''),
            ('', ''),
            ('', ''),
            ('', ''),
            ('', ''),
        ]
        for (expected_name, expected_email), sample in zip(expected, samples):
            parsed = self.env['res.partner']._parse_partner_name(sample)
            self.assertEqual(parsed[0], expected_name)
            self.assertEqual(parsed[1], expected_email)

    def test_res_partner_find_or_create(self):
        PartnerModel = self.env['res.partner']

        partner = PartnerModel.browse(PartnerModel.name_create(SAMPLES[0][0])[0])
        self._check_find_or_create(
            SAMPLES[0][0], SAMPLES[0][1], SAMPLES[0][2],
            check_partner=partner, should_create=False
        )

        partner_2 = PartnerModel.browse(PartnerModel.name_create('sarah.john@connor.com')[0])
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

        existing = PartnerModel.create({
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

    @users('employee_c2')
    def test_res_partner_find_or_create_from_emails(self):
        """ Test for _find_or_create_from_emails allowing to find or create
        partner based on emails in a batch-enabled and optimized fashion. """
        self.user_employee_c2.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)],
        })

        samples_emails = [item[0] for item in SAMPLES]
        partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
            samples_emails,
            additional_values=None,
        )
        self.assertEqual(len(partners), len(SAMPLES))
        for (sample, exp_name, exp_email), partner in zip(SAMPLES, partners):
            exp_email_normalized = tools.email_normalize(exp_email)
            self.assertFalse(partner.company_id)
            self.assertEqual(partner.email_normalized, exp_email_normalized)
            self.assertTrue(partner.id)
            self.assertEqual(partner.lang, 'en_US')
            self.assertEqual(partner.name, exp_name)

        new_samples = SAMPLES + [
            ('"New Customer" <new.customer@test.EXAMPLE.com>', 'New Customer', 'new.customer@test.example.com'),
            ('"Duplicated Raoul" <RAOUL@chirurgiens-dentistes.fr>', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
            ('Invalid', 'Invalid', ''),
            (False, False, False),
            (None, False, False),
            (' ', False, False),
            ('', False, False),
        ]
        samples_emails = [item[0] for item in new_samples]
        partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
            samples_emails,
            additional_values={'company_id': self.env.company.id},
        )
        self.assertEqual(len(partners), len(new_samples))
        for (sample, exp_name, exp_email), partner in zip(new_samples, partners):
            with self.subTest(sample=sample, exp_name=exp_name, exp_email=exp_email, partner=partner):
                exp_company = self.env.company if sample in [
                    '"New Customer" <new.customer@test.EXAMPLE.com>',  # valid email, not known -> new customer
                    'Invalid'  # invalid email, not known -> create a new partner
                ] else self.env['res.company']
                if sample in [False, None, ' ', '']:
                    self.assertFalse(partner)
                else:
                    exp_email_normalized = tools.email_normalize(exp_email)
                    self.assertEqual(partner.company_id, exp_company)
                    self.assertEqual(partner.email_normalized, exp_email_normalized)
                    self.assertEqual(partner.name, exp_name)

    @users('employee_c2')
    def test_res_partner_find_or_create_from_emails_dupes(self):
        """ Specific test for duplicates management: based on email to avoid
        creating similar partners. """
        self.user_employee_c2.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)],
        })

        # all same partner, same email 'test.customer@test.dupe.example.com'
        email_dupes_samples = [
            '"Formatted Customer" <test.customer@TEST.DUPE.EXAMPLE.COM>',
            'test.customer@test.dupe.example.com',
            '"Another Name" <test.customer@TEST.DUPE.EXAMPLE.COM>',
            '"Mix of both" <test.customer@test.dupe.EXAMPLE.COM',
        ]
        email_expected_name = "Formatted Customer"  # first found email will setup partner info
        email_expected_email = 'test.customer@test.dupe.example.com'  # normalized version of given email
        # all same partner, same invalid email 'test.customer.invalid.email'
        name_dupes_samples = [
            'test.customer.invalid.email',
            'test.customer.invalid.email',
        ]
        name_expected_name = 'test.customer.invalid.email'  # invalid email kept as both name and email
        name_expected_email = 'test.customer.invalid.email'  # invalid email kept as both name and email

        partners = self.env['res.partner']
        for samples, (expected_name, expected_email) in [
            (email_dupes_samples, (email_expected_name, email_expected_email)),
            (name_dupes_samples, (name_expected_name, name_expected_email)),
        ]:
            with self.subTest(samples=samples, expected_name=expected_name, expected_email=expected_email):
                with self.mockPartnerCalls():
                    partner_list = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
                        samples,
                        additional_values=None,
                    )
                # calls
                self.assertEqual(self._mock_partner_create.call_count, 1)
                self.assertEqual(self._mock_partner_search.call_count, 1)
                self.assertEqual(len(self._new_partners), 1)
                # results
                self.assertEqual(len(partner_list), len(samples))
                self.assertTrue(len(set(partner.id for partner in partner_list)) == 1 and partner_list[0].id, 'Should have a unique new partner')
                for partner in partner_list:
                    self.assertEqual(partner.email, expected_email)
                    self.assertEqual(partner.name, expected_name)

                partners += partner_list[0]

        self.assertEqual(len(partners), 2,
                         'Should have created one partner for valid email, one for invalid email')

        new_samples = [
            '"Another Customer" <test.customer2@TEST.DUPE.EXAMPLE.COM',  # actually a new valid email
            '"First Duplicate" <test.customer@TEST.DUPE.example.com',  # duplicated of valid email created above
            'test.customer.invalid.email',  # duplicate of an invalid email created above
        ]
        with self.mockPartnerCalls():
            new_partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
                new_samples,
                additional_values=None,
            )
        # calls
        self.assertEqual(self._mock_partner_create.call_count, 1)
        self.assertEqual(self._mock_partner_search.call_count, 1,
                         'Search once, even with both normalized and invalid emails')
        self.assertEqual(len(self._new_partners), 1)
        # results
        self.assertEqual(len(new_partners), len(new_samples))
        self.assertEqual(new_partners[0].email, "test.customer2@test.dupe.example.com")
        self.assertEqual(new_partners[0].name, "Another Customer")
        self.assertEqual(new_partners[1], partners[0])

        other_samples = [
            '"Another Duplicate" <test.customer2@TEST.DUPE.EXAMPLE.COM',
            '"First Duplicate2" <test.customer@TEST.DUPE.example.com',
            '"Third Customer" <test.customer3@test.dupe.example.com',
            '"Falsy" <falsy>',
            'falsy',
            '  ',
        ]
        with self.mockPartnerCalls():
            other_partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
                other_samples,
                additional_values=None,
            )
        # calls
        self.assertEqual(self._mock_partner_create.call_count, 1)
        self.assertEqual(self._mock_partner_search.call_count, 1)
        self.assertEqual(len(self._new_partners), 3)
        # results
        self.assertEqual(len(other_partners), len(other_samples))
        self.assertEqual(other_partners[0], new_partners[0], 'Should take already existing partner')
        self.assertEqual(other_partners[1], partners[0], 'Should take already existing partner')
        self.assertEqual(other_partners[2].email, "test.customer3@test.dupe.example.com")
        self.assertEqual(other_partners[2].name, "Third Customer")
        self.assertEqual(other_partners[3].email, '"Falsy" <falsy>')
        self.assertEqual(other_partners[3].name, '"Falsy" <falsy>')
        self.assertEqual(other_partners[4].email, "falsy")
        self.assertEqual(other_partners[4].name, "falsy")

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
        # return format for user is either a dict (there is a user and the dict is data) or a list of command (clear)
        self.assertEqual(list(map(lambda p: isinstance(p['user'], dict) and p['user']['isInternalUser'], partners_format)), [True, True, False, False, False], "should return internal users in priority")
        self.assertEqual(list(map(lambda p: isinstance(p['user'], dict), partners_format)), [True, True, True, True, False], "should return partners without users last")

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
