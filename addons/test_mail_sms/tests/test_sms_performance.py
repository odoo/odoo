from odoo import Command
from odoo.tests import tagged
from odoo.tests.common import users, warmup
from odoo.tools import mute_logger

from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests.test_performance import BaseMailPerformance


@tagged("mail_performance", "post_install", "-at_install")
class TestSMSPerformance(BaseMailPerformance, sms_common.SMSCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record = (
            cls.env["mail.test.sms"]
            .with_context(cls._test_context)
            .create(
                {
                    "name": "Test",
                    "customer_id": cls.customer.id,
                    "phone_nbr_ids": [Command.create({"number": "0456999999"})],
                }
            )
        )

        # prepare recipients to test for more realistic workload
        cls.partners = (
            cls.env["res.partner"]
            .with_context(cls._test_context)
            .create(
                [
                    {
                        "country_id": cls.env.ref("base.be").id,
                        "email": "test%s@example.com" % x,
                        "phone_ids": [
                            Command.create(
                                {"number": "0456%s%s0000" % (x, x), "type": "landline"}
                            )
                        ],
                        "name": "Test %s" % x,
                    }
                    for x in range(10)
                ]
            )
        )

    @mute_logger("odoo.addons.sms.models.sms_sms")
    @users("employee")
    @warmup
    def test_message_sms_record_1_partner(self):
        record = self.test_record.with_user(self.env.user)
        pids = self.customer.ids
        with (
            self.subTest("QueryCount"),
            self.mockSMSGateway(sms_allow_unlink=True),
            # +5 (and +8 below, which resolves the record's number and the
            # customer's): a number is a phone.number row reached through a
            # relation, not a column of the record, and the company's mail
            # configuration is another row. The cost is the same for one
            # partner as for ten, so the batch still holds.
            # +1: the company's mail configuration is a row of its own (mixin.company.config), read once per transaction on a cold cache.
            self.assertQueryCount(employee=37),
        ):  # tms: 36
            messages = record._message_sms(
                body="Performance Test",
                partner_ids=pids,
            )

        self.assertEqual(record.message_ids[0].body, "<p>Performance Test</p>")
        self.assertSMSNotification(
            [{"partner": self.customer}], "Performance Test", messages, sent_unlink=True
        )

    @mute_logger("odoo.addons.sms.models.sms_sms")
    @users("employee")
    @warmup
    def test_message_sms_record_10_partners(self):
        record = self.test_record.with_user(self.env.user)
        pids = self.partners.ids
        with (
            self.subTest("QueryCount"),
            self.mockSMSGateway(sms_allow_unlink=True),
            # +5: the number is a phone.number row, not a column (see above).
            # +1: the company's mail configuration is a row of its own (mixin.company.config), read once per transaction on a cold cache.
            self.assertQueryCount(employee=37),
        ):  # tms: 36
            messages = record._message_sms(
                body="Performance Test",
                partner_ids=pids,
            )

        self.assertEqual(record.message_ids[0].body, "<p>Performance Test</p>")
        self.assertSMSNotification(
            [{"partner": partner} for partner in self.partners],
            "Performance Test",
            messages,
            sent_unlink=True,
        )

    @mute_logger("odoo.addons.sms.models.sms_sms")
    @users("employee")
    @warmup
    def test_message_sms_record_default(self):
        record = self.test_record.with_user(self.env.user)
        with (
            self.subTest("QueryCount"),
            self.mockSMSGateway(sms_allow_unlink=True),
            # +8: the record's number and the customer's (see above).
            # +1: the company's mail configuration is a row of its own (mixin.company.config), read once per transaction on a cold cache.
            self.assertQueryCount(employee=41),
        ):  # tms: 40
            messages = record._message_sms(
                body="Performance Test",
            )

        self.assertEqual(record.message_ids[0].body, "<p>Performance Test</p>")
        self.assertSMSNotification(
            [{"number": "+32456999999", "partner": self.customer}],
            "Performance Test",
            messages,
            sent_unlink=True,
        )


@tagged("mail_performance", "post_install", "-at_install")
class TestSMSMassPerformance(BaseMailPerformance, sms_common.MockSMS):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        be_country_id = cls.env.ref("base.be").id

        cls._test_body = "MASS SMS"

        records = cls.env["mail.test.sms"]
        partners = cls.env["res.partner"]
        for x in range(50):
            partners += (
                cls.env["res.partner"]
                .with_context(**cls._test_context)
                .create(
                    {
                        "name": "Partner_%s" % (x),
                        "email": "_test_partner_%s@example.com" % (x),
                        "country_id": be_country_id,
                        "phone_ids": [
                            Command.create(
                                {
                                    "number": "047500%02d%02d" % (x, x),
                                    "type": "landline",
                                }
                            )
                        ],
                    }
                )
            )
            records += (
                cls.env["mail.test.sms"]
                .with_context(**cls._test_context)
                .create(
                    {
                        "name": "Test_%s" % (x),
                        "customer_id": partners[x].id,
                    }
                )
            )
        cls.partners = partners
        cls.records = records

        cls.sms_template = cls.env["sms.template"].create(
            {
                "name": "Test Template",
                "model_id": cls.env["ir.model"]._get("mail.test.sms").id,
                "body": "Dear {{ object.display_name }} this is an SMS.",
            }
        )

    @mute_logger("odoo.addons.sms.models.sms_sms")
    @users("employee")
    @warmup
    def test_sms_composer_mass(self):
        composer = (
            self.env["sms.composer"]
            .with_context(
                default_composition_mode="mass",
                default_res_model="mail.test.sms",
                active_ids=self.records.ids,
            )
            .create(
                {
                    "body": self._test_body,
                    "mass_keep_log": False,
                }
            )
        )

        with (
            self.mockSMSGateway(sms_allow_unlink=True),
            self.assertQueryCount(employee=60),
        ):
            composer.action_send_sms()

    @mute_logger("odoo.addons.sms.models.sms_sms")
    @users("employee")
    @warmup
    def test_sms_composer_mass_w_log(self):
        composer = (
            self.env["sms.composer"]
            .with_context(
                default_composition_mode="mass",
                default_res_model="mail.test.sms",
                active_ids=self.records.ids,
            )
            .create(
                {
                    "body": self._test_body,
                    "mass_keep_log": True,
                }
            )
        )

        with (
            self.mockSMSGateway(sms_allow_unlink=True),
            self.assertQueryCount(employee=64),
        ):
            composer.action_send_sms()
