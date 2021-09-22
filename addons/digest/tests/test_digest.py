import itertools
import random

from dateutil.relativedelta import relativedelta
from lxml import html

from odoo import fields
from odoo.addons.mail.tests import common as mail_test


class TestDigest(mail_test.MailCommon):
    def test_digest_numbers(self):
        self._setup_messages()

        digest = self.env['digest.digest'].create({
            'name': "My Digest",
            'kpi_mail_message_total': True
        })

        digest_user = digest.with_user(self.user_employee)
        # subscribe a user so at least one mail gets sent
        digest_user.action_subscribe()
        self.assertTrue(
            digest_user.is_subscribed,
            "check the user was subscribed as action_subscribe will silently "
            "ignore subs of non-employees"
        )

        # digest creates its mails in auto_delete mode so we need to capture
        # the formatted body during the sending process
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(len(self._mails), 1, "a mail has been created for the digest")
        body = self._mails[0]['body']

        kpi_message_values = html.fromstring(body).xpath('//div[@data-field="kpi_mail_message_total"]//*[hasclass("kpi_value")]/text()')
        self.assertEqual(
            [t.strip() for t in kpi_message_values],
            ['3', '8', '15']
        )

    def _setup_messages(self):
        """ Remove all existing messages, then create a bunch of them on random
        partners with the correct types in correct time-bucket:

        - 3 in the previous 24h
        - 5 more in the 6 days before that for a total of 8 in the previous week
        - 7 more in the 20 days before *that* (because digest doc lies and is
          based around weeks and months not days), for a total of 15 in the
          previous month
        """
        self.env['mail.message'].search([]).unlink()
        now = fields.Datetime.now()
        # regular employee can't necessarily access "private" addresses
        partners = self.env['res.partner'].search([('type', '!=', 'private')])
        counter = itertools.count()

        # pylint: disable=bad-whitespace
        for count, (low, high) in [
            (3, (0 * 24,  1 * 24)),
            (5, (1 * 24,  7 * 24)),
            (7, (7 * 24, 27 * 24)),
        ]:
            for _ in range(count):
                create_date = now - relativedelta(hours=random.randint(low + 1, high - 1))
                random.choice(partners).message_post(
                    body=f"Awesome Partner! ({next(counter)})",
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    # adjust top and bottom by 1h to avoid overlapping with the
                    # range limit and dropping out of the digest's selection thing
                    create_date=create_date
                )
