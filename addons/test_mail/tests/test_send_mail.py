from unittest.mock import patch

from . import common
from odoo import SUPERUSER_ID
from odoo.addons.mail.models.mail_thread import MailThread


class TestSendMailSudo(common.BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        """
        Since we want to test from whom an email is sent,
        we won't assert with the helper self.formataddr_superuser
        Otherwise, the snake bites its tail!
        Hence, we'll hardcode the expected email address
        """
        super(TestSendMailSudo, cls).setUpClass()
        cls.mail_thread_model = cls.env['res.partner']

        cls.super_user = cls.env['res.users'].browse(SUPERUSER_ID)
        cls.super_user.company_id.email = 'timmy.thomas@livetogether.com'

        cls.company2 = cls.env['res.company'].create({
            'name': 'company2',
            'email': 'company2@company2.com',
        })

        cls.super_user.write({
            'company_ids': [(4, cls.company2.id, False)],
        })

        cls.partner_test = cls.mail_thread_model.create({
            'name': 'Steve Winwood',
        })
        cls.partner_test2 = cls.mail_thread_model.create({
            'name': 'Gary Clark',
            'company_id': cls.company2.id,
        })

    def test_empty_superuser_email(self):
        # Explicit assert
        # Ensure the rest of tested use cases rely on this
        self.assertFalse(self.super_user.partner_id.email)

    def test_sudo_post_simple_company(self):
        # always explicitly do it as sudo
        mail_message = self.partner_test.sudo().message_post()

        self.assertEqual(mail_message.email_from, '"OdooBot (YourCompany)" <timmy.thomas@livetogether.com>')

    def test_sudo_post_multicompanies0(self):
        # always explicitly do it as sudo
        mail_message = self.partner_test2.sudo().message_post()

        self.assertEqual(mail_message.email_from, '"OdooBot (company2)" <company2@company2.com>')

    def test_sudo_assign_activity(self):
        self.assertsCount = 0

        original_message_post = MailThread.message_post

        def patched_msg_post(*args, **kwargs):
            mail_message = original_message_post(*args, **kwargs)
            self.assertEqual(mail_message.email_from, '"OdooBot (YourCompany)" <timmy.thomas@livetogether.com>')
            self.assertsCount += 1

        demo_user = self.env.ref('base.user_demo')
        PartnerModel = self.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        with patch('odoo.addons.mail.models.mail_thread.MailThread.message_post', patched_msg_post):
            self.env['mail.activity'].create({
                'res_id': self.partner_test2.id,
                'res_model_id': PartnerModel.id,
                'user_id': demo_user.id,
            })

        self.assertEqual(self.assertsCount, 1)
