# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests.common import SMSCommon
from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients


class TestSMSCommon(SMSCommon, TestMailCommon):
    """ Main entry point for functional tests. Kept to ease backward
    compatibility and updating common. """


class TestSMSRecipients(TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSMSRecipients, cls).setUpClass()
        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in (cls.partner_1 | cls.partner_2)
        ]
