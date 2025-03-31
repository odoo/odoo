# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged, users
from odoo.addons.mail.tools.parser import domain_eval
from freezegun import freeze_time


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

    def test_mail_find_partner_from_emails_multicompany(self):
        """ Test _mail_find_partner_from_emails when dealing with records in
        a multicompany environment, returning a partner record with matching
        company_id. """
        Partner = self.env['res.partner']
        self.test_partner.company_id = self.company_2

        test_partner_no_company = self.test_partner.copy({'company_id': False})
        test_partner_company_2 = self.test_partner
        test_partner_company_3 = test_partner_no_company.copy({'company_id': self.company_3.id})
        records = [
            None,
            *Partner.create([
                {'name': 'Company 2 contact', 'company_id': self.company_2.id},
                {'name': 'Company 3 contact', 'company_id': self.company_3.id},
                {'name': 'No restrictions', 'company_id': False},
            ])
        ]
        expected_partners = [
            (test_partner_no_company, "W/out reference record, prefer non-specific partner."),
            (test_partner_company_2, "Prefer same company as reference record."),
            (test_partner_company_3, "Prefer same company as reference record."),
            (test_partner_no_company, "Prefer non-specific partner for non-specific records."),
        ]
        for record, (expected_partner, msg) in zip(records, expected_partners):
            found = Partner._mail_find_partner_from_emails([self._test_email], records=record)
            self.assertEqual(found, [expected_partner], msg)

    @freeze_time('2030-05-24')
    def test_domain_eval(self):
        success_pairs = [
            ("list()", []),
            ("list(range(1, 4))", [1, 2, 3]),
            ("['|', (1, '=', 1), (1, '>', 0)]", ['|', (1, '=', 1), (1, '>', 0)]),
            ("[(2, '=', 1 + 1)]", [(2, '=', 2)]),
            (
                "[('create_date', '<', datetime.datetime.combine(context_today() - relativedelta(days=100), datetime.time(1, 2, 3)).to_utc().strftime('%Y-%m-%d %H:%M:%S'))]",
                [('create_date', '<', "2030-02-13 01:02:03")],
            ),  # use the date utils used by front-end domains
        ]
        for domain_expression, domain_value in success_pairs:
            with self.subTest(domain_expression=domain_expression, domain_value=domain_value):
                self.assertEqual(domain_eval(domain_expression), domain_value)


@tagged('mail_tools', 'mail_init')
class TestMailUtils(MailCommon):

    def test_migrate_icp_to_domain(self):
        """ Test ICP to alias domain migration """
        self.env["ir.config_parameter"].set_param("mail.catchall.domain", "test.migration.com")
        self.env["ir.config_parameter"].set_param("mail.bounce.alias", "migrate+bounce")
        self.env["ir.config_parameter"].set_param("mail.catchall.alias", "migrate+catchall")
        self.env["ir.config_parameter"].set_param("mail.default.from", "migrate+default_from")

        existing = self.env["mail.alias.domain"].search([('name', '=', 'test.migration.com')])
        self.assertFalse(existing)

        new = self.env["mail.alias.domain"]._migrate_icp_to_domain()
        self.assertEqual(new.name, "test.migration.com")
        self.assertEqual(new.bounce_alias, "migrate+bounce")
        self.assertEqual(new.catchall_alias, "migrate+catchall")
        self.assertEqual(new.default_from, "migrate+default_from")

        again = self.env["mail.alias.domain"]._migrate_icp_to_domain()
        self.assertEqual(again.name, "test.migration.com")

        existing = self.env["mail.alias.domain"].search([('name', '=', 'test.migration.com')])
        self.assertEqual(len(existing), 1, 'Should not migrate twice')
