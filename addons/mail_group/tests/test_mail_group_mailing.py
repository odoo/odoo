from ast import literal_eval

from odoo.addons.mail_group.tests.common import TestMailListCommon
from odoo.tests.common import HttpCase, tagged, users


@tagged("mail_group", "mail_mail", "post_install", "-at_install")
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
            _response = self.url_open(unsubscribe_url, method='POST')

        self.assertEqual(test_group.member_ids, self.test_group_member_4_emp,
                         "Mail Group: people should have been unsubscribed")

    def test_unsubscribe_oneclick_non_ascii_token(self):
        """ A non-ascii token is rejected like any other wrong token """
        test_group = self.test_group.with_env(self.env)
        members = test_group.member_ids

        response = self.url_open(
            '/group/%s/unsubscribe_oneclick' % test_group.id,
            data={'token': 'é' * 64, 'email': self.test_group_member_1.email_normalized},
        )

        self.assertEqual(response.status_code, 404)
        test_group.invalidate_recordset(['member_ids'])
        self.assertEqual(test_group.member_ids, members,
                         "Mail Group: nobody should have been unsubscribed")
