# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users
from odoo import tools


@tagged('mail_tools')
class TestMailTools(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailTools, cls).setUpClass()

        cls._test_email = 'alfredoastaire@test.example.com'
        cls.test_partner = cls.env['res.partner'].create({
            'country_id': cls.env.ref('base.be').id,
            'email': cls._test_email,
            'mobile': '0456001122',
            'name': 'Alfred Astaire',
            'phone': '0456334455',
        })

        cls.sources = [
            # single email
            'alfred.astaire@test.example.com',
            ' alfred.astaire@test.example.com ',
            'Fredo The Great <alfred.astaire@test.example.com>',
            '"Fredo The Great" <alfred.astaire@test.example.com>',
            'Fredo "The Great" <alfred.astaire@test.example.com>',
            # multiple emails
            'alfred.astaire@test.example.com, evelyne.gargouillis@test.example.com',
            'Fredo The Great <alfred.astaire@test.example.com>, Evelyne The Goat <evelyne.gargouillis@test.example.com>',
            '"Fredo The Great" <alfred.astaire@test.example.com>, evelyne.gargouillis@test.example.com',
            '"Fredo The Great" <alfred.astaire@test.example.com>, <evelyne.gargouillis@test.example.com>',
            # text containing email
            'Hello alfred.astaire@test.example.com how are you ?',
            '<p>Hello alfred.astaire@test.example.com</p>',
            # text containing emails
            'Hello "Fredo" <alfred.astaire@test.example.com>, evelyne.gargouillis@test.example.com',
            'Hello "Fredo" <alfred.astaire@test.example.com> and evelyne.gargouillis@test.example.com',
            # falsy
            '<p>Hello Fredo</p>',
            'j\'adore écrire des @gmail.com ou "@gmail.com" a bit randomly',
            '',
        ]

    @users('employee')
    def test_mail_find_partner_from_emails(self):
        Partner = self.env['res.partner']
        test_partner = Partner.browse(self.test_partner.ids)
        self.assertEqual(test_partner.email, self._test_email)

        sources = [
            self._test_email,  # test direct match
            f'"Norbert Poiluchette" <{self._test_email}>',  # encapsulated
            'fredoastaire@test.example.com',  # partial email -> should not match !
        ]
        expected_partners = [
            test_partner,
            test_partner,
            self.env['res.partner'],
        ]
        for source, expected_partner in zip(sources, expected_partners):
            with self.subTest(source=source):
                found = Partner._mail_find_partner_from_emails([source])
                self.assertEqual(found, [expected_partner])

        # test with wildcard "_"
        found = Partner._mail_find_partner_from_emails(['alfred_astaire@test.example.com'])
        self.assertEqual(found, [self.env['res.partner']])
        # sub-check: this search does not consider _ as a wildcard
        found = Partner._mail_search_on_partner(['alfred_astaire@test.example.com'])
        self.assertEqual(found, self.env['res.partner'])

        # test partners with encapsulated emails
        # ------------------------------------------------------------
        test_partner.sudo().write({'email': f'"Alfred Mighty Power Astaire" <{self._test_email}>'})

        sources = [
            self._test_email,  # test direct match
            f'"Norbert Poiluchette" <{self._test_email}>',  # encapsulated
        ]
        expected_partners = [
            test_partner,
            test_partner,
        ]
        for source, expected_partner in zip(sources, expected_partners):
            with self.subTest(source=source):
                found = Partner._mail_find_partner_from_emails([source])
                self.assertEqual(found, [expected_partner])

        # test with wildcard "_"
        found = Partner._mail_find_partner_from_emails(['alfred_astaire@test.example.com'])
        self.assertEqual(found, [self.env['res.partner']])
        # sub-check: this search does not consider _ as a wildcard
        found = Partner._mail_search_on_partner(['alfred_astaire@test.example.com'])
        self.assertEqual(found, self.env['res.partner'])

    @users('admin')
    def test_mail_find_partner_from_emails_followers(self):
        """ Test '_mail_find_partner_from_emails' when dealing with records on
        which followers have to be found based on email. Check multi email
        and encapsulated email support. """
        # create partner just for the follow mechanism
        linked_record = self.env['res.partner'].sudo().create({'name': 'Record for followers'})
        follower_partner = self.env['res.partner'].sudo().create({
            'email': self._test_email,
            'name': 'Duplicated, follower of record',
        })
        linked_record.message_subscribe(partner_ids=follower_partner.ids)
        test_partner = self.test_partner.with_env(self.env)

        # standard test, no multi-email, to assert base behavior
        sources = [(self._test_email, True), (self._test_email, False),]
        expected = [follower_partner, test_partner]
        for (source, follower_check), expected in zip(sources, expected):
            with self.subTest(source=source, follower_check=follower_check):
                partner = self.env['res.partner']._mail_find_partner_from_emails(
                    [source], records=linked_record if follower_check else None
                )[0]
                self.assertEqual(partner, expected)

        # formatted email
        encapsulated_test_email = f'"Robert Astaire" <{self._test_email}>'
        (follower_partner + test_partner).sudo().write({'email': encapsulated_test_email})
        sources = [
            (self._test_email, True),  # normalized
            (self._test_email, False),  # normalized
            (encapsulated_test_email, True),  # encapsulated, same
            (encapsulated_test_email, False),  # encapsulated, same
            (f'"AnotherName" <{self._test_email}', True),  # same normalized, other name
            (f'"AnotherName" <{self._test_email}', False),  # same normalized, other name
        ]
        expected = [follower_partner, test_partner,
                    follower_partner, test_partner,
                    follower_partner, test_partner,
                    follower_partner, test_partner]
        for (source, follower_check), expected in zip(sources, expected):
            with self.subTest(source=source, follower_check=follower_check):
                partner = self.env['res.partner']._mail_find_partner_from_emails(
                    [source], records=linked_record if follower_check else None
                )[0]
                self.assertEqual(partner, expected,
                                'Mail: formatted email is recognized through usage of normalized email')

        # multi-email
        _test_email_2 = '"Robert Astaire" <not.alfredoastaire@test.example.com>'
        (follower_partner + test_partner).sudo().write({'email': f'{self._test_email}, {_test_email_2}'})
        sources = [
            (self._test_email, True),  # first email
            (self._test_email, False),  # first email
            (_test_email_2, True),  # second email
            (_test_email_2, False),  # second email
            ('not.alfredoastaire@test.example.com', True),  # normalized second email in field
            ('not.alfredoastaire@test.example.com', False),  # normalized second email in field
            (f'{self._test_email}, {_test_email_2}', True),  # multi-email, both matching, depends on comparison
            (f'{self._test_email}, {_test_email_2}', False)  # multi-email, both matching, depends on comparison
        ]
        expected = [follower_partner, test_partner,
                    self.env['res.partner'], self.env['res.partner'],
                    self.env['res.partner'], self.env['res.partner'],
                    follower_partner, test_partner]
        for (source, follower_check), expected in zip(sources, expected):
            with self.subTest(source=source, follower_check=follower_check):
                partner = self.env['res.partner']._mail_find_partner_from_emails(
                    [source], records=linked_record if follower_check else None
                )[0]
                self.assertEqual(partner, expected,
                                'Mail (FIXME): partial recognition of multi email through email_normalize')

        # test users with same email, priority given to current user
        # --------------------------------------------------------------
        self.user_employee.sudo().write({'email': '"Alfred Astaire" <%s>' % self.env.user.partner_id.email_normalized})
        found = self.env['res.partner']._mail_find_partner_from_emails([self.env.user.partner_id.email_formatted])
        self.assertEqual(found, [self.env.user.partner_id])

    @users('employee')
    def test_tools_email_re(self):
        expected = [
            # single email
            ['alfred.astaire@test.example.com'],
            ['alfred.astaire@test.example.com'],
            ['alfred.astaire@test.example.com'],
            ['alfred.astaire@test.example.com'],
            ['alfred.astaire@test.example.com'],
            # multiple emails
            ['alfred.astaire@test.example.com', 'evelyne.gargouillis@test.example.com'],
            ['alfred.astaire@test.example.com', 'evelyne.gargouillis@test.example.com'],
            ['alfred.astaire@test.example.com', 'evelyne.gargouillis@test.example.com'],
            ['alfred.astaire@test.example.com', 'evelyne.gargouillis@test.example.com'],
            # text containing email
            ['alfred.astaire@test.example.com'],
            ['alfred.astaire@test.example.com'],
            # text containing emails
            ['alfred.astaire@test.example.com', 'evelyne.gargouillis@test.example.com'],
            ['alfred.astaire@test.example.com', 'evelyne.gargouillis@test.example.com'],
            # falsy
            [], [], [],
        ]

        for src, exp in zip(self.sources, expected):
            res = tools.email_re.findall(src)
            self.assertEqual(
                res, exp,
                'Seems email_re is broken with %s (expected %r, received %r)' % (src, exp, res)
            )

    @users('employee')
    def test_tools_email_split_tuples(self):
        expected = [
            # single email
            [('', 'alfred.astaire@test.example.com')],
            [('', 'alfred.astaire@test.example.com')],
            [('Fredo The Great', 'alfred.astaire@test.example.com')],
            [('Fredo The Great', 'alfred.astaire@test.example.com')],
            [('Fredo The Great', 'alfred.astaire@test.example.com')],
            # multiple emails
            [('', 'alfred.astaire@test.example.com'), ('', 'evelyne.gargouillis@test.example.com')],
            [('Fredo The Great', 'alfred.astaire@test.example.com'), ('Evelyne The Goat', 'evelyne.gargouillis@test.example.com')],
            [('Fredo The Great', 'alfred.astaire@test.example.com'), ('', 'evelyne.gargouillis@test.example.com')],
            [('Fredo The Great', 'alfred.astaire@test.example.com'), ('', 'evelyne.gargouillis@test.example.com')],
            # text containing email -> fallback on parsing to extract text from email
            [('Hello', 'alfred.astaire@test.example.comhowareyou?')],
            [('Hello', 'alfred.astaire@test.example.com')],
            [('Hello Fredo', 'alfred.astaire@test.example.com'), ('', 'evelyne.gargouillis@test.example.com')],
            [('Hello Fredo', 'alfred.astaire@test.example.com'), ('and', 'evelyne.gargouillis@test.example.com')],
            # falsy -> probably not designed for that
            [],
            [('j\'adore écrire', "des@gmail.comou"), ('', '@gmail.com')], [],
        ]

        for src, exp in zip(self.sources, expected):
            res = tools.email_split_tuples(src)
            self.assertEqual(
                res, exp,
                'Seems email_split_tuples is broken with %s (expected %r, received %r)' % (src, exp, res)
            )

    @users('employee')
    def test_tools_single_email_re(self):
        expected = [
            # single email
            ['alfred.astaire@test.example.com'],
            [], [], [], [], # formatting issue for single email re
            # multiple emails -> couic
            [], [], [], [],
            # text containing email -> couic
            [], [],
            # text containing emails -> couic
            [], [],
            # falsy
            [], [], [],
        ]

        for src, exp in zip(self.sources, expected):
            res = tools.single_email_re.findall(src)
            self.assertEqual(
                res, exp,
                'Seems single_email_re is broken with %s (expected %r, received %r)' % (src, exp, res)
            )
