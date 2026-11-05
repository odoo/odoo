# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged


@tagged('mail_template')
class TestMailTemplateAuthor(MailCommon):
    """ Author of emails sent from a template without sender ('Send From'),
    depending on the 'Send as Responsible' toggle of the template. """

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

    def test_template_default(self):
        """ Toggle is enabled by default and template has no sender """
        self.assertTrue(self.test_template.email_from_responsible)
        self.assertFalse(self.test_template.email_from)

    def test_template_author_automated(self):
        """ Automated sending (OdooBot, e.g. crons): responsible when toggle is
        enabled, OdooBot when disabled (standard behavior). """
        for toggle, exp_author in (
            (True, self.partner_employee),
            (False, self.partner_root),
        ):
            for sending in ('composer', 'send_mail'):
                with self.subTest(toggle=toggle, sending=sending), self.mock_mail_gateway():
                    self.test_template.email_from_responsible = toggle
                    author, email_from = self._send_with_template(self.user_root, sending)
                    self.assertEqual(author, exp_author)
                    self.assertEqual(email_from, exp_author.email_formatted)

    def test_template_author_public(self):
        """ Public user (e.g. website / payment flow, in sudo): responsible when
        toggle is enabled. """
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                author, email_from = self._send_with_template(self.user_public, sending, sudo=True)
                self.assertEqual(author, self.partner_employee)
                self.assertEqual(email_from, self.partner_employee.email_formatted)

    def test_template_author_real_user(self):
        """ A real user sending is always the author, whatever the toggle """
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
        """ Template with a sender: sender is kept, toggle has no effect """
        self.test_template.email_from = '{{ object.customer_id.email_formatted }}'
        for sending in ('composer', 'send_mail'):
            with self.subTest(sending=sending), self.mock_mail_gateway():
                _author, email_from = self._send_with_template(self.user_root, sending)
                self.assertEqual(email_from, self.customer.email_formatted)
