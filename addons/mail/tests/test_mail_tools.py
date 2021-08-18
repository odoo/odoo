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
    def test_find_partner_from_emails(self):
        Partner = self.env['res.partner']
        test_partner = Partner.browse(self.test_partner.ids)
        self.assertEqual(test_partner.email, self._test_email)

        # test direct match
        found = Partner._mail_find_partner_from_emails([self._test_email])
        self.assertEqual(found, [test_partner])

        # test encapsulated email
        found = Partner._mail_find_partner_from_emails(['"Norbert Poiluchette" <%s>' % self._test_email])
        self.assertEqual(found, [test_partner])

        # test with wildcard "_"
        found = Partner._mail_find_partner_from_emails(['alfred_astaire@test.example.com'])
        self.assertEqual(found, [self.env['res.partner']])

        # sub-check: this search does not consider _ as a wildcard
        found = Partner._mail_search_on_partner(['alfred_astaire@test.example.com'])
        self.assertEqual(found, self.env['res.partner'])

        # test partners with encapsulated emails
        # ------------------------------------------------------------
        test_partner.sudo().write({'email': '"Alfred Mighty Power Astaire" <%s>' % self._test_email})

        # test direct match
        found = Partner._mail_find_partner_from_emails([self._test_email])
        self.assertEqual(found, [test_partner])

        # test encapsulated email
        found = Partner._mail_find_partner_from_emails(['"Norbert Poiluchette" <%s>' % self._test_email])
        self.assertEqual(found, [test_partner])

        # test with wildcard "_"
        found = Partner._mail_find_partner_from_emails(['alfred_astaire@test.example.com'])
        self.assertEqual(found, [self.env['res.partner']])

        # sub-check: this search does not consider _ as a wildcard
        found = Partner._mail_search_on_partner(['alfred_astaire@test.example.com'])
        self.assertEqual(found, self.env['res.partner'])

        # test partners with look-alike emails
        # ------------------------------------------------------------
        for email_lookalike in [
                'alfred.astaire@test.example.com',
                'alfredoastaire@example.com',
                'aalfredoastaire@test.example.com',
                'alfredoastaire@test.example.comm']:
            test_partner.sudo().write({'email': '"Alfred Astaire" <%s>' % email_lookalike})

            # test direct match
            found = Partner._mail_find_partner_from_emails([self._test_email])
            self.assertEqual(found, [self.env['res.partner']])
            # test encapsulated email
            found = Partner._mail_find_partner_from_emails(['"Norbert Poiluchette" <%s>' % self._test_email])
            self.assertEqual(found, [self.env['res.partner']])
            # test with wildcard "_"
            found = Partner._mail_find_partner_from_emails(['alfred_astaire@test.example.com'])
            self.assertEqual(found, [self.env['res.partner']])

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
            # text containing email -> probably not designed for that
            [('', 'Hello alfred.astaire@test.example.comhowareyou?')],
            [('', 'Hello alfred.astaire@test.example.com')],
            # text containing emails -> probably not designed for that
            [('Hello Fredo', 'alfred.astaire@test.example.com'), ('', 'evelyne.gargouillis@test.example.com')],
            [('Hello Fredo', 'alfred.astaire@test.example.com'), ('', 'and evelyne.gargouillis@test.example.com')],
            # falsy -> probably not designed for that
            [], [('', "j'adore écrire des@gmail.comou"), ('', '@gmail.com')], [],
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
