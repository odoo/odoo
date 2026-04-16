# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('-at_install', 'post_install')
class TestInvitationLink(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user = cls.env.ref('base.group_user')
        cls.Link = cls.env['hr.invitation.link']
        cls.Users = cls.env['res.users']

    def _signup(self, link, login, name='New Person', password='Sup3rPwd!x'):
        return self.Users.with_context(hr_invite_link_id=link.id).signup(
            {'name': name, 'login': login, 'password': password})

    def test_token_and_url_generated(self):
        link = self.Link.create({})
        self.assertTrue(link.access_token)
        self.assertEqual(len(link.access_token), 32)
        self.assertTrue(link.url.endswith('/hr/invite/%s' % link.access_token))

    def test_validity_expired(self):
        link = self.Link.create({'expiration_datetime': fields.Datetime.now() - timedelta(days=1)})
        ok, _reason = link._is_valid()
        self.assertFalse(ok)

    def test_validity_disabled(self):
        link = self.Link.create({'active': False})
        ok, _reason = link._is_valid()
        self.assertFalse(ok)

    def test_validity_max_uses(self):
        link = self.Link.create({'max_uses': 2, 'used_count': 2})
        ok, _reason = link._is_valid()
        self.assertFalse(ok)

    def test_validity_unlimited(self):
        link = self.Link.create({'max_uses': 0, 'used_count': 999})
        ok, _reason = link._is_valid()
        self.assertTrue(ok)

    def test_domain_restriction(self):
        link = self.Link.create({'allowed_email_domains': 'odoo.com\nexample.org'})
        self.assertTrue(link._is_email_domain_allowed('jane@odoo.com'))
        self.assertTrue(link._is_email_domain_allowed('joe@example.org'))
        self.assertFalse(link._is_email_domain_allowed('joe@gmail.com'))
        # no restriction => any domain
        self.assertTrue(self.Link.create({})._is_email_domain_allowed('a@b.com'))

    def test_invalid_domain_rejected(self):
        with self.assertRaises(ValidationError):
            self.Link.create({'allowed_email_domains': 'not a domain'})

    def test_signup_creates_lite_employee(self):
        link = self.Link.create({'max_uses': 5})
        login, _pwd = self._signup(link, 'newbie@example.com')
        user = self.Users.search([('login', '=', login)])
        self.assertTrue(user, "the invited user must be created")
        self.assertFalse(user.share, "the invited user is an internal user")
        self.assertEqual(user.role, 'light',
                         "the invited user must be a Light, non-billable user")
        self.assertTrue(user.employee_ids, "an employee must be created for the invited user")
        self.assertEqual(link.used_count, 1, "the link use must be recorded")

    def test_signup_respects_company(self):
        company = self.env['res.company'].create({'name': 'Invite Co'})
        link = self.Link.create({'company_id': company.id})
        login, _pwd = self._signup(link, 'cny@example.com')
        employee = self.Users.search([('login', '=', login)]).employee_ids
        self.assertEqual(employee.company_id, company)

    @mute_logger('odoo.sql_db')
    def test_signup_domain_blocked(self):
        link = self.Link.create({'allowed_email_domains': 'odoo.com'})
        with self.assertRaises(Exception):
            self._signup(link, 'outsider@gmail.com')
        self.assertEqual(link.used_count, 0)

    @mute_logger('odoo.sql_db')
    def test_max_uses_enforced(self):
        link = self.Link.create({'max_uses': 1})
        self._signup(link, 'first@example.com')
        self.assertEqual(link.used_count, 1)
        with self.assertRaises(UserError):
            self._signup(link, 'second@example.com')
        self.assertEqual(link.used_count, 1, "an over-quota signup must not be recorded")
