# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_parse

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon
from odoo.addons.test_mail_sms.tests.common import TestSMSRecipients
from odoo.tests import tagged, users


class TestMailThreadInternalsCommon(TestMailFullCommon, TestSMSRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMailThreadInternalsCommon, cls).setUpClass()

        cls.test_portal_records, cls.test_portal_partners = cls._create_records_for_batch(
            'mail.test.portal',
            2,
        )
        cls.test_portal_nop_records, _ = cls._create_records_for_batch(
            'mail.test.portal.no.partner',
            2,
        )
        cls.test_rating_records, cls.test_rating_partners = cls._create_records_for_batch(
            'mail.test.rating',
            2,
        )
        cls.test_simple_records, _ = cls._create_records_for_batch(
            'mail.test.simple',
            2,
        )


@tagged('mail_thread', 'portal')
class TestMailThreadInternals(TestMailThreadInternalsCommon):

    @users('employee')
    def test_notify_get_recipients_groups(self):
        """ Test redirection of portal-enabled records """
        test_records = [
            self.test_portal_records[0].with_env(self.env),
            self.test_portal_nop_records[0].with_env(self.env),
            self.test_rating_records[0].with_env(self.env),
            self.test_simple_records[0].with_env(self.env),
        ]
        for test_record in test_records:
            with self.subTest(test_record=test_record):
                is_portal = test_record._name != 'mail.test.simple'
                has_customer = test_record._name != 'mail.test.portal.no.partner'

                if is_portal:
                    self.assertFalse(
                        test_record.access_token,
                        'By default access tokens are False with portal'
                    )

                groups = test_record._notify_get_recipients_groups()
                portal_customer_group = next(
                    (group for group in groups if group[0] == 'portal_customer'),
                    False
                )

                if is_portal and has_customer:
                    # should have generated the access token, required for portal links
                    self.assertFalse(
                        test_record.access_token,
                        'TODO: Method not called, access token is not generated'
                    )
                    # check portal_customer content and link
                    self.assertFalse(
                        portal_customer_group,
                        'TODO: MEthod not called, group is not present'
                    )
                else:
                    self.assertFalse(
                        portal_customer_group,
                        'Portal Mixin should not add portal customer notification group'
                    )
