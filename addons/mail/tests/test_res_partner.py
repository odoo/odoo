# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from markupsafe import Markup
from unittest.mock import patch
from uuid import uuid4

from odoo import tools
from odoo.addons.base.models.res_partner import Partner
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.tests import Form, tagged, users
from odoo.tools import mute_logger


@tagged('res_partner', 'mail_tools')
class TestPartner(MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.samples = [
            ('"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
            ('ryu+giga-Sushi@aizubange.fukushima.jp', 'ryu+giga-sushi@aizubange.fukushima.jp', 'ryu+giga-sushi@aizubange.fukushima.jp'),
            ('Raoul chirurgiens-dentistes.fr', 'Raoul chirurgiens-dentistes.fr', ''),
            (" Raoul O'hara  <!@historicalsociety.museum>", "Raoul O'hara", '!@historicalsociety.museum'),
            ('Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
            ('Raoul megaraoul@chirurgiens-dentistes.fr', 'Raoul', 'megaraoul@chirurgiens-dentistes.fr'),
            ('"Patrick Da Beast Poilvache" <PATRICK@example.com>', 'Patrick Da Beast Poilvache', 'patrick@example.com'),
            ('Patrick Caché <patrick@EXAMPLE.COM>', 'Patrick Da Beast Poilvache', 'patrick@example.com'),
            ('Patrick Caché <patrick.2@EXAMPLE.COM>', 'Patrick Caché', 'patrick.2@example.com'),
            # multi email
            ('"Multi Email" <multi.email@example.com>, multi.email.2@example.com', 'Multi Email', 'multi.email@example.com')
        ]
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

    def _check_find_or_create(self, test_string, expected_name, expected_email,
                              expected_email_normalized=False,
                              expected_partner=False):
        expected_email_normalized = expected_email_normalized or tools.email_normalize(expected_email) or ''
        with self.mockPartnerCalls():
            partner = self.env['res.partner'].find_or_create(test_string)
        if expected_partner:
            self.assertEqual(
                partner, expected_partner,
                f'Should have found {expected_partner.name} ({expected_partner.id}), found {partner.name} ({partner.id}) instead')
            self.assertFalse(self._new_partners)
        else:
            self.assertEqual(
                partner, self._new_partners,
                f'Should have created a partner, found {partner.name} ({partner.id}) instead'
            )
        self.assertEqual(partner.name, expected_name)
        self.assertEqual(partner.email or '', expected_email)
        self.assertEqual(partner.email_normalized or '', expected_email_normalized)
        return partner

    def test_address_tracking(self):
        self.env.company.name = 'YourCompany'
        company_partner = self.env.company.partner_id
        # use some wacky formatting to check inlining
        company_partner.country_id.address_format = """%(street)s
            \n\n\n%(street2)s
            %(city)s %(state_code)s %(zip)s
            \n%(country_name)s\n
            \n   """
        company_partner.write({
            'city': 'Some City Name',
            'street': 'Some Street Name',
            'type': 'contact',
            'zip': '94134',
            'state_id': self.env.ref('base.state_us_5').id,
            'country_id': self.env.ref('base.us').id,
        })
        child_partner = self.env['res.partner'].create({
            'name': 'Some Guy',
            'parent_id': company_partner.id,
        })
        self.env.flush_all()
        self.cr.precommit.run()
        # keep track of setup messages
        partners = (company_partner, child_partner)
        partner_original_messages = (company_partner.message_ids, child_partner.message_ids)

        company_partner.street = 'Some Other Street Name'
        company_partner.city = 'Some Other City Name'
        self.env.flush_all()
        self.cr.precommit.run()
        for partner, original_messages in zip(partners, partner_original_messages):
            change_messages = partner.message_ids - original_messages
            self.assertEqual(len(change_messages), 1)
            tracking_values = change_messages.tracking_value_ids
            self.assertIn(f'{self.env.company.name}, Some Street Name, Some City Name CA 94134, United States',
                          tracking_values.old_value_char)
            self.assertIn(f'{self.env.company.name}, Some Other Street Name, Some Other City Name CA 94134, United States',
                          tracking_values.new_value_char)
            # none of the address fields are logged at the same time
            self.assertEqual(set(), set(partner._address_fields()) & set(tracking_values.sudo().field_id.mapped('name')))

    def test_discuss_mention_suggestions_priority(self):
        name = uuid4()  # unique name to avoid conflict with already existing users
        self.env['res.partner'].create([{'name': f'{name}-{i}-not-user'} for i in range(0, 2)])
        for i in range(0, 2):
            mail_new_test_user(self.env, login=f'{name}-{i}-portal-user', groups='base.group_portal')
            mail_new_test_user(self.env, login=f'{name}-{i}-internal-user', groups='base.group_user')
        partners_format = self.env["res.partner"].get_mention_suggestions(name, limit=5)[
            "res.partner"
        ]
        self.assertEqual(len(partners_format), 5, "should have found limit (5) partners")
        # return format for user is either a dict (there is a user and the dict is data) or a list of command (clear)
        self.assertEqual(list(map(lambda p: p['isInternalUser'], partners_format)), [True, True, False, False, False], "should return internal users in priority")
        self.assertEqual(list(map(lambda p: bool(p['userId']), partners_format)), [True, True, True, True, False], "should return partners without users last")

    @users('admin')
    def test_find_or_create(self):
        """ Test 'find_or_create' method, calling name_create while parsing
        input to find name and email. """
        original_partner = self.env['res.partner'].browse(
            self.env['res.partner'].name_create(self.samples[0][0])[0]
        )
        all_partners = []

        for (text_input, expected_name, expected_email), expected_partner, find_idx in zip(
            self.samples,
            [original_partner, False, False, False, original_partner, False,
             # patrick example
             False, False, False,
             # multi email
             False],
            [0, 0, 0, 0, 0, 0, 0, 6, 0, 0],
        ):
            with self.subTest(text_input=text_input):
                if not expected_partner and find_idx:
                    expected_partner = all_partners[find_idx]
                all_partners.append(
                    self._check_find_or_create(
                        text_input, expected_name, expected_email,
                        expected_partner=expected_partner,
                    )
                )

        with self.assertRaises(ValueError):
            self.env['res.partner'].find_or_create("Raoul chirurgiens-dentistes.fr", assert_valid_email=True)

    @users('admin')
    def test_find_or_create_email_field(self):
        """ Test 'find_or_create' tool used in mail, notably when linking emails
        found in recipients to partners when sending emails using the mail
        composer. Test various combinations of problematic use cases like
        formatting, multi-emails, ... """
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

        # now input is multi email -> 'parse_contact_from_email' used in 'find_or_create'
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

    @users('employee_c2')
    def test_find_or_create_from_emails(self):
        """ Test for '_find_or_create_from_emails' allowing to find or create
        partner based on emails in a batch-enabled and optimized fashion. """
        self.user_employee_c2.write({
            'groups_id': [(4, self.env.ref('base.group_partner_manager').id)],
        })

        with self.mockPartnerCalls():
            partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
                [item[0] for item in self.samples],
                additional_values=None,
            )
        self.assertEqual(len(partners), len(self.samples))
        self.assertEqual(len(self._new_partners), len(self.samples) - 2, 'Two duplicates in samples')

        for (sample, exp_name, exp_email), partner in zip(self.samples, partners):
            # specific to '_from_emails': name used as email is no email found
            exp_email = exp_email or exp_name
            with self.subTest(sample=sample):
                self.assertFalse(partner.company_id)
                self.assertEqual(partner.email, exp_email)
                self.assertEqual(partner.email_normalized, tools.email_normalize(exp_email))
                self.assertTrue(partner.id)
                self.assertEqual(partner.lang, 'en_US')
                self.assertEqual(partner.name, exp_name)

        new_samples = self.samples + [
            # new
            ('"New Customer" <new.customer@test.EXAMPLE.com>', 'New Customer', 'new.customer@test.example.com'),
            # duplicate (see in sample)
            ('"Duplicated Raoul" <RAOUL@chirurgiens-dentistes.fr>', 'Raoul Grosbedon', 'raoul@chirurgiens-dentistes.fr'),
            # new (even if invalid)
            ('Invalid', 'Invalid', ''),
            # ignored, completely invalid
            (False, False, False),
            (None, False, False),
            (' ', False, False),
            ('', False, False),
        ]
        all_emails = [item[0] for item in new_samples]
        with self.mockPartnerCalls():
            partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
                all_emails,
                additional_values={
                    tools.email_normalize(email): {
                        'company_id': self.env.company.id,
                    }
                    for email in all_emails
                },
            )
        self.assertEqual(len(partners), len(new_samples))
        self.assertEqual(len(self._new_partners), 2, 'Only 2 real new partners in new sample')

        for (sample, exp_name, exp_email), partner in zip(new_samples, partners):
            with self.subTest(sample=sample, exp_name=exp_name, exp_email=exp_email, partner=partner):
                # specific to '_from_emails': name used as email is no email found
                exp_email = exp_email or exp_name
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
    def test_res_partner_find_or_create_from_emails_dupes_email_field(self):
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
            '"Another Customer" <test.different.1@TEST.DUPE.EXAMPLE.COM',  # actually a new valid email
            '"First Duplicate" <test.customer@TEST.DUPE.example.com',  # duplicated of valid email created above
            'test.customer.invalid.email',  # duplicate of an invalid email created above
            # multi email
            '"Multi Email Another" <TEST.different.1@test.dupe.example.com>, other.customer@other.example.com',
            '"Multi Email" <other.customer.2@test.dupe.example.com>, test.different.1@test.dupe.example.com',
            'Invalid, Multi Format other.customer.😊@test.dupe.example.com, "A Name" <yt.another.customer@new.example.com>',
            '"Unicode Formatted" <other.customer.😊@test.dupe.example.com>',  # duplicate of above
        ]
        expected = [
            (False, "Another Customer", "test.different.1@test.dupe.example.com"),
            (partners[0], "Formatted Customer", "test.customer@test.dupe.example.com"),
            (partners[1], "test.customer.invalid.email", "test.customer.invalid.email"),
            # multi email support
            (False, "Another Customer", "test.different.1@test.dupe.example.com"),
            (False, "Multi Email", "other.customer.2@test.dupe.example.com"),
            (False, "Multi Format", "other.customer.😊@test.dupe.example.com"),
            (False, "Multi Format", "other.customer.😊@test.dupe.example.com"),
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
        self.assertEqual(len(self._new_partners), 3)
        self.assertEqual(
            sorted(self._new_partners.mapped('email')),
            sorted(['other.customer.2@test.dupe.example.com',
                    'other.customer.😊@test.dupe.example.com',
                    'test.different.1@test.dupe.example.com']))
        # results
        self.assertEqual(len(new_partners), len(new_samples))
        for partner, (expected_partner, expected_name, expected_email) in zip(new_partners, expected):
            with self.subTest(partner=partner, expected_name=expected_name):
                if expected_partner:
                    self.assertEqual(partner, expected_partner)
                else:
                    self.assertIn(partner, self._new_partners)
                self.assertEqual(partner.email, expected_email)
                self.assertEqual(partner.name, expected_name)

        no_new_samples = [
            # only duplicates
            '"Another Duplicate" <test.different.1@TEST.DUPE.EXAMPLE.COM',
            '"First Duplicate2" <test.customer@TEST.DUPE.example.com',
            # falsy values
            '"Falsy" <falsy>',
            'falsy',
            '  ',
        ]
        expected = [
            (new_partners[0], "Another Customer", "test.different.1@test.dupe.example.com"),
            (partners[0], "Formatted Customer", "test.customer@test.dupe.example.com"),
            (False, '"Falsy" <falsy>', '"Falsy" <falsy>'),
            (False, "falsy", "falsy"),
            (False, False, False),
        ]
        with self.mockPartnerCalls():
            no_new_partners = self.env['res.partner'].with_context(lang='en_US')._find_or_create_from_emails(
                no_new_samples,
                additional_values=None,
            )
        # calls
        self.assertEqual(self._mock_partner_create.call_count, 1)
        self.assertEqual(self._mock_partner_search.call_count, 1)
        self.assertEqual(len(self._new_partners), 2)
        self.assertEqual(sorted(self._new_partners.mapped('email')), ['"Falsy" <falsy>', "falsy"])
        for partner, (expected_partner, expected_name, expected_email) in zip(no_new_partners, expected):
            with self.subTest(partner=partner, expected_name=expected_name):
                if expected_partner:
                    self.assertEqual(partner, expected_partner)
                elif not expected_name and not expected_email:
                    self.assertEqual(partner, self.env['res.partner'])
                else:
                    self.assertIn(partner, self._new_partners)
                self.assertEqual(partner.email, expected_email)
                self.assertEqual(partner.name, expected_name)

    def test_log_portal_group(self):
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

    @users('admin')
    def test_name_create_corner_cases(self):
        """ Test parsing (and fallback) or name given to name_create that should
        try to correctly find name and email, even with malformed input. Relies
        on 'parse_contact_from_email' and 'email_normalize'. """
        samples = [
            'Raoul raoul@grosbedon.fr',
            'Raoul chirurgiens-dentistes.fr',
            'invalid',
            'False',
            # (simili) void values
            '', ' ', False, None,
            # email only
            'lenny.bar@gmail.com',
        ]
        expected = [
            ('Raoul', 'raoul@grosbedon.fr'),
            ('Raoul chirurgiens-dentistes.fr', False),
            ('invalid', False),
            ('False', False),
            # (simili) void values: always False
            ('', False), ('', False), ('', False), ('', False),
            # email only: email used as both name and email
            ('lenny.bar@gmail.com', 'lenny.bar@gmail.com')
        ]
        for (expected_name, expected_email), sample in zip(expected, samples):
            with self.subTest(sample=sample):
                partner = self.env['res.partner'].browse(
                    self.env['res.partner'].name_create(sample)[0]
                )
                self.assertEqual(partner.name, expected_name)
                self.assertEqual(partner.email, expected_email)

    @users('admin')
    @mute_logger('odoo.addons.base.partner.merge', 'odoo.tests')
    def test_partner_merge_wizards(self):
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
            body=Markup('<p>Log on P1</p>'),
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
