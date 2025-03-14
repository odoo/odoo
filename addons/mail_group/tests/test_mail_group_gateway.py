from ast import literal_eval

from odoo.addons.mail_group.tests.common import TestMailListCommon
from odoo.addons.mail_group.tests.data import GROUP_TEMPLATE
from odoo.tests.common import HttpCase, tagged, users


@tagged("mail_group", "mail_gateway", "post_install", "-at_install")
class TestMailGroupGateway(TestMailListCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_group.moderation = False
        cls.test_group_other = cls.env['mail.group'].create({
            'access_mode': 'public',
            'alias_name': 'test.mail.group.other',
            'moderation': False,
            'name': 'Other test group',
        })
        cls.test_alias_other = cls.env['mail.alias'].create({
            'alias_domain_id': cls.mail_alias_domain.id,
            'alias_contact': 'everyone',
            'alias_model_id': cls.env['ir.model']._get_id('res.partner'),
            'alias_name': 'alias.partner',
        })

    def test_gateway_forward_to_other_list(self):
        """ Test forwarding an email from a mailing list to another one. """
        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.test_group_member_1.email,
                self.test_group.alias_email,
                subject='Hello', msg_id='<glory.to.the.hypnotoad@localhost>', target_model='mail.group')

        last_message = self.test_group.mail_group_message_ids[-1]
        self.assertEqual(last_message.email_from, self.test_group_member_1.email)
        self.assertEqual(last_message.subject, 'Hello')

        mail = self._find_mail_mail_wemail('member_2@test.com', 'outgoing')
        self.assertTrue(mail)
        with self.mock_mail_gateway():
            self._gateway_mail_reply(
                GROUP_TEMPLATE, mail=mail,
                force_email_to=self.test_group_other.alias_email,
                target_model=self.test_group._name,
                debug_log=True,
            )

        last_message = self.test_group.mail_group_message_ids[-1]
        self.assertEqual(last_message.email_from, self.test_group_member_2.email)
        self.assertEqual(last_message.subject, 'Re: Hello')

    def test_gateway_forward_to_other_model(self):
        """ Test forwarding an email from a mailing list to another one. """
        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.test_group_member_1.email,
                self.test_group.alias_email,
                subject='Hello', msg_id='<glory.to.the.hypnotoad@localhost>', target_model='mail.group')

        last_message = self.test_group.mail_group_message_ids[-1]
        self.assertEqual(last_message.email_from, self.test_group_member_1.email)
        self.assertEqual(last_message.subject, 'Hello')

        mail = self._find_mail_mail_wemail('member_2@test.com', 'outgoing')
        self.assertTrue(mail)
        with self.mock_mail_gateway():
            new_record = self._gateway_mail_reply(
                GROUP_TEMPLATE, mail=mail,
                force_email_to=self.test_alias_other.alias_full_name,
                target_model='res.partner',
                debug_log=True,
            )

        self.assertEqual(self.test_group.mail_group_message_ids[-1], last_message)
        self.assertTrue(new_record)

    def test_gateway_reply(self):
        """ Test replying to an email from a mailing list """
        with self.mock_mail_gateway():
            self.format_and_process(
                GROUP_TEMPLATE, self.test_group_member_1.email,
                self.test_group.alias_email,
                subject='Hello', msg_id='<glory.to.the.hypnotoad@localhost>', target_model='mail.group')

        last_message = self.test_group.mail_group_message_ids[-1]
        self.assertEqual(last_message.email_from, self.test_group_member_1.email)
        self.assertEqual(last_message.subject, 'Hello')

        mail = self._find_mail_mail_wemail('member_2@test.com', 'outgoing')
        self.assertTrue(mail)
        with self.mock_mail_gateway():
            self._gateway_mail_reply(
                GROUP_TEMPLATE, mail=mail,
                target_model=self.test_group._name,
                debug_log=True,
            )

        last_message = self.test_group.mail_group_message_ids[-1]
        self.assertEqual(last_message.email_from, self.test_group_member_2.email)
        self.assertEqual(last_message.subject, 'Re: Hello')


@tagged("mail_group", "mail_gateway", "mail_mail", "post_install", "-at_install")
class TestMailGroupMailing(TestMailListCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_group.moderation = False

    @users("employee")
    def test_mail_mail_headers(self):
        """ Test headers notably unsubscribe headers """
        test_group = self.test_group.with_env(self.env)
        # don't contact yourself, banned people receive outgoing emails
        expected_recipients = self.test_group_member_1 + self.test_group_member_2 + self.test_group_member_3_banned

        with self.mock_mail_gateway(mail_unlink_sent=False):
            test_group.message_post(
                body="<p>Test Body</p>",
            )

        self.assertEqual(len(self._new_mails), len(expected_recipients))

        for member in expected_recipients:
            mail = self._find_mail_mail_wemail(member.email, "outgoing")
            unsubscribe_url = literal_eval(mail.headers).get("List-Unsubscribe").strip('<>')
            _response = self.url_open(unsubscribe_url)

        self.assertEqual(test_group.member_ids, self.test_group_member_4_emp,
                         "Mail Group: people should have been unsubscribed")
