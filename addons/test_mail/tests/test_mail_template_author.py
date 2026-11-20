# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged


@tagged('mail_template')
class TestMailTemplateAuthor(MailCommon):
    """ Author of emails sent from a template without sender ('Send From'):
    record responsible for automated sending, current user otherwise. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env['res.partner'].create({
            'email': 'customer@example.com',
            'name': 'Customer',
        })
        cls.test_record = cls.env['mail.test.ticket'].create({
            'customer_id': cls.customer.id,
            'name': 'Ticket',
            'user_id': cls.user_employee.id,
        })
        cls.test_template = cls.env['mail.template'].create({
            'body_html': '<p>Hello</p>',
            'model_id': cls.env['ir.model']._get_id('mail.test.ticket'),
            'name': 'Test Template Without Sender',
            'subject': 'Your ticket',
            'use_default_to': True,
        })

    def _send_with_template(self, user, sending, sudo=False):
        """ Send test template on test record as given user, either through
        the composer (message_post_with_source) or through send_mail. Return
        (author, email_from) of the generated message / mail. """
        record = self.test_record.with_user(user).sudo(sudo)
        template = self.test_template.with_user(user).sudo(sudo)
        if sending == 'composer':
            message = record.message_post_with_source(
                template,
                subtype_xmlid='mail.mt_comment',
            )
            return message.author_id, message.email_from
        mail = self.env['mail.mail'].sudo().browse(template.send_mail(record.id))
        return mail.author_id, mail.email_from

    def test_template_author_automated(self):
        """ Automated sending (OdooBot, e.g. crons): record responsible """
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                author, email_from = self._send_with_template(self.user_root, sending)
                self.assertEqual(author, self.partner_employee)
                self.assertEqual(email_from, self.partner_employee.email_formatted)

    def test_template_author_automated_current_user(self):
        """ Automated sending with sender set to current user: OdooBot is kept
        (way to opt out of the responsible fallback). """
        self.test_template.email_from = '{{ user.email_formatted }}'
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                author, email_from = self._send_with_template(self.user_root, sending)
                self.assertEqual(author, self.partner_root)
                self.assertEqual(email_from, self.partner_root.email_formatted)

    def test_template_author_public(self):
        """ Public user (e.g. website / payment flow, in sudo): record responsible """
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                author, email_from = self._send_with_template(self.user_public, sending, sudo=True)
                self.assertEqual(author, self.partner_employee)
                self.assertEqual(email_from, self.partner_employee.email_formatted)

    def test_template_author_real_user(self):
        """ A real user sending is always the author """
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                author, email_from = self._send_with_template(self.user_admin, sending)
                self.assertEqual(author, self.partner_admin)
                self.assertEqual(email_from, self.partner_admin.email_formatted)

    def test_template_author_no_responsible(self):
        """ No responsible on record: fallback on company """
        self.test_record.user_id = False
        company_partner = self.env.company.partner_id
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                author, email_from = self._send_with_template(self.user_root, sending)
                self.assertEqual(author, company_partner)
                self.assertEqual(email_from, company_partner.email_formatted)

    def test_template_author_with_sender(self):
        """ Template with a sender: sender is kept """
        self.test_template.email_from = '{{ object.customer_id.email_formatted }}'
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                _author, email_from = self._send_with_template(self.user_root, sending)
                self.assertEqual(email_from, self.customer.email_formatted)

    def test_template_author_automated_note(self):
        """ Automated note posted from a template (e.g. tracking template,
        automatic logs): current user (OdooBot) is kept as author. """
        with self.mock_mail_gateway():
            message = self.test_record.with_user(self.user_root).message_post_with_source(
                self.test_template,
                subtype_xmlid='mail.mt_note',
            )
        self.assertEqual(message.author_id, self.partner_root)
        self.assertEqual(message.email_from, self.partner_root.email_formatted)

    def test_template_signature(self):
        """ Signature rendered in template body through '_mail_get_default_signature'
        matches the default author: responsible for automated sending, current
        user otherwise, nothing when falling back on the company. """
        self.test_template.body_html = '<p>Hello</p><t t-out="object._mail_get_default_signature()"/>'
        self.user_employee.signature = '<p>Employee Signature</p>'
        self.user_admin.signature = '<p>Admin Signature</p>'
        for user, has_responsible, expected, not_expected in [
            (self.user_root, True, 'Employee Signature', 'Admin Signature'),
            (self.user_admin, True, 'Admin Signature', 'Employee Signature'),
            (self.user_root, False, False, 'Signature'),
        ]:
            self.test_record.user_id = self.user_employee if has_responsible else False
            for sending in ('composer', 'send_mail'):
                with self.subTest(user=user.name, has_responsible=has_responsible, sending=sending), \
                     self.mock_mail_gateway():
                    record = self.test_record.with_user(user)
                    if sending == 'composer':
                        body = record.message_post_with_source(
                            self.test_template.with_user(user),
                            subtype_xmlid='mail.mt_comment',
                        ).body
                    else:
                        mail_id = self.test_template.with_user(user).send_mail(record.id)
                        body = self.env['mail.mail'].sudo().browse(mail_id).body_html
                    if expected:
                        self.assertIn(expected, body)
                    self.assertNotIn(not_expected, body)
