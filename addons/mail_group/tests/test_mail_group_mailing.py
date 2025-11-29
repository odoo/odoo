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

    def test_group_view_messages_date_filter(self):
        """Test that date filtering works correctly in group_view_messages controller"""
        url = f'/groups/{self.test_group.id}'
        response = self.url_open(url, params={
            'date_begin': '2025-11-01',
            'date_end': '2025-12-01'
        })

        self.assertEqual(response.status_code, 200)
