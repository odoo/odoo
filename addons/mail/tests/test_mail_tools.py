# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users


@tagged('mail_tools', 'res_partner')
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

    @users('employee')
    def test_find_partner_from_emails(self):
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

    @users('employee')
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
