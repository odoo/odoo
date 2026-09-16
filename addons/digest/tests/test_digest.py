from datetime import UTC, date, datetime
from unittest.mock import patch
from urllib.parse import urlencode

from dateutil.relativedelta import relativedelta
from lxml import html

from odoo import SUPERUSER_ID, fields
from odoo.exceptions import AccessError
from odoo.fields import Command, Domain
from odoo.libs.web import urls
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.digest.models.digest import KPI_AGGREGATE_MEMO, PERIODICITIES
from odoo.addons.digest.tests.common import TestDigestCommon
from odoo.addons.mail.tests.common import MailCommon


class TestDigest(TestDigestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reference_datetime = datetime(2024, 2, 13, 13, 30, 0)

        # clean messages
        cls.env["mail.message"].search(
            [
                ("subtype_id", "=", cls.env.ref("mail.mt_comment").id),
                ("message_type", "in", ("comment", "email", "email_outgoing")),
            ]
        ).unlink()
        cls._setup_messages()

        # clean demo users so that we keep only the test users
        cls.env["res.users"].search(
            [("login", "in", ["demo", "portal"])]
        ).action_archive()
        # clean logs so that town down can be tested
        cls.env["res.users.log"].search(
            [("create_uid", "in", (cls.user_admin + cls.user_employee).ids)]
        ).unlink()
        # create logs for user_admin
        cls._setup_logs_for_users(
            cls.user_admin, cls.reference_datetime - relativedelta(days=5)
        )

        with cls.mock_datetime_and_now(cls, cls.reference_datetime):
            cls.test_digest, cls.test_digest_2 = cls.env["digest.digest"].create(
                [
                    {
                        "kpi_mail_message_total": True,
                        "kpi_res_users_connected": True,
                        "name": "My Digest",
                        "periodicity": "daily",
                    },
                    {
                        "kpi_mail_message_total": True,
                        "kpi_res_users_connected": True,
                        "name": "My Digest",
                        "periodicity": "weekly",
                        "user_ids": [(4, cls.user_admin.id), (4, cls.user_employee.id)],
                    },
                ]
            )

    @users("admin")
    def test_assert_initial_values(self):
        """Ensure base values for tests"""
        test_digest = self.test_digest.with_user(self.env.user)
        test_digest_2 = self.test_digest_2.with_user(self.env.user)
        self.assertEqual(test_digest.create_date, self.reference_datetime)
        self.assertEqual(
            test_digest.next_run_date,
            self.reference_datetime.date() + relativedelta(days=1),
        )
        self.assertEqual(test_digest.periodicity, "daily")
        self.assertFalse(test_digest.user_ids)

        self.assertEqual(test_digest_2.create_date, self.reference_datetime)
        self.assertEqual(
            test_digest_2.next_run_date,
            self.reference_datetime.date() + relativedelta(weeks=1),
        )
        self.assertEqual(test_digest_2.periodicity, "weekly")
        self.assertEqual(test_digest_2.user_ids, self.user_admin + self.user_employee)

    @users("admin")
    def test_digest_kpi_res_users_connected_value(self):
        self.env["res.users.log"].with_user(SUPERUSER_ID).search([]).unlink()
        # Sanity check
        initial_values = self.all_digests.mapped("kpi_res_users_connected_value")
        self.assertEqual(initial_values, [0, 0, 0])

        self.env["res.users"].with_user(self.user_employee)._update_last_login()
        self.env["res.users"].with_user(self.user_admin)._update_last_login()

        self.all_digests.invalidate_recordset()

        self.assertEqual(self.digest_1.kpi_res_users_connected_value, 2)
        self.assertEqual(
            self.digest_2.kpi_res_users_connected_value,
            0,
            msg="This KPI is in an other company",
        )
        self.assertEqual(
            self.digest_3.kpi_res_users_connected_value,
            2,
            msg="This KPI has no company, should take the current one",
        )

    @users("admin")
    def test_digest_numbers(self):
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        digest._action_subscribe_users(self.user_employee)

        # digest creates its mails in auto_delete mode so we need to capture
        # the formatted body during the sending process
        digest.flush_recordset()
        with self.mock_mail_gateway():
            digest.action_send()

        self.assertEqual(
            len(self._new_mails), 1, "A new mail.mail should have been created"
        )
        mail = self._new_mails[0]
        # check mail.mail content
        self.assertEqual(mail.author_id, self.partner_admin)
        self.assertEqual(mail.email_from, self.company_admin.email_formatted)
        self.assertEqual(mail.state, "outgoing", "Mail should use the queue")

        kpi_message_values = html.fromstring(mail.body_html).xpath(
            '//table[@data-field="kpi_mail_message_total"]//*[hasclass("kpi_value")]/text()'
        )
        self.assertEqual([t.strip() for t in kpi_message_values], ["3", "8", "15"])

    @users("admin")
    def test_digest_subscribe(self):
        digest_user = self.digest_1.with_user(self.user_employee)
        self.assertFalse(digest_user.is_subscribed)

        # subscribe a user so at least one mail gets sent
        digest_user.action_subscribe()
        self.assertTrue(
            digest_user.is_subscribed,
            "check the user was subscribed as action_subscribe will silently "
            "ignore subs of non-employees",
        )
        digest_user.action_unsubscribe()
        self.assertFalse(digest_user.is_subscribed)

    @users("admin")
    def test_digest_tip_description(self):
        self.env["digest.tip"].create(
            {
                "name": "Test digest tips",
                "tip_description": """
                <t t-set="record_exists" t-value="True" />
                <t t-if="record_exists">
                    <p class="rendered">Record exists.</p>
                </t>
                <t t-else="">
                    <p class="not-rendered">Record doesn't exist.</p>
                </t>
            """,
            }
        )
        with self.mock_mail_gateway():
            self.digest_1._action_send_to_user(self.user_employee)
        self.assertEqual(
            len(self._new_mails), 1, "A new Email should have been created"
        )
        sent_mail_body = html.fromstring(self._new_mails.body_html)
        values_to_check = [
            sent_mail_body.xpath('//t[@t-set="record_exists"]'),
            sent_mail_body.xpath('//p[@class="rendered"]/text()'),
            sent_mail_body.xpath('//p[@class="not-rendered"]/text()'),
        ]
        self.assertEqual(
            values_to_check,
            [[], ["Record exists."], []],
            "Sent mail should contain properly rendered tip content",
        )

    @users("admin")
    def test_digest_tone_down(self):
        test_digest = self.env["digest.digest"].browse(self.test_digest.ids)
        test_digest_2 = self.env["digest.digest"].browse(self.test_digest_2.ids)
        test_digest._action_subscribe_users(self.user_employee)
        digests = test_digest + test_digest_2  # batch recordset

        # no logs for employee but for admin -> should tone down periodicity of
        # first digest, not the second one (admin being subscribed)
        digests.flush_recordset()
        current_dt = self.reference_datetime + relativedelta(days=1)
        with self.mock_datetime_and_now(current_dt), self.mock_mail_gateway():
            digests.action_send()

        self.assertEqual(
            test_digest.next_run_date, current_dt.date() + relativedelta(weeks=1)
        )
        self.assertEqual(test_digest.periodicity, "weekly")
        self.assertEqual(
            test_digest_2.next_run_date, current_dt.date() + relativedelta(weeks=1)
        )
        self.assertEqual(
            test_digest_2.periodicity,
            "weekly",
            "Should not have tone down because admin has logs",
        )

        # no logs for employee -> should tone down periodicity
        with self.mock_datetime_and_now(current_dt), self.mock_mail_gateway():
            digests.action_send()

        self.assertEqual(
            test_digest.next_run_date, current_dt.date() + relativedelta(months=1)
        )
        self.assertEqual(test_digest.periodicity, "monthly")
        self.assertEqual(
            test_digest_2.next_run_date, current_dt.date() + relativedelta(weeks=1)
        )
        self.assertEqual(test_digest_2.periodicity, "weekly")

        # no logs for employee -> should tone down periodicity
        with self.mock_datetime_and_now(current_dt), self.mock_mail_gateway():
            digests.action_send()

        self.assertEqual(
            test_digest.next_run_date, current_dt.date() + relativedelta(months=3)
        )
        self.assertEqual(test_digest.periodicity, "quarterly")
        self.assertEqual(
            test_digest_2.next_run_date, current_dt.date() + relativedelta(weeks=1)
        )
        self.assertEqual(test_digest_2.periodicity, "weekly")

    @users("admin")
    def test_digest_tone_down_wlogs(self):
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        digest._action_subscribe_users(self.user_employee)

        for logs, (periodicity, run_date), (exp_periodicity, exp_run_date, msg) in zip(
            [
                # daily
                [(self.user_employee, self.reference_datetime)],
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(days=1, hours=23),
                    )
                ],  # two days logs -> do not tone down
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(days=2, hours=1),
                    )
                ],  # > two days logs -> tone down
                [],  # no logs -> tone down
                # weekly
                [(self.user_employee, self.reference_datetime - relativedelta(days=6))],
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(days=8),
                    )
                ],  # old logs -> tone down
                [],  # no logs -> tone down
                # monthly
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(days=25),
                    )
                ],
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(days=32),
                    )
                ],  # old logs -> tone down
                [],  # no logs -> tone down
                # quarterly
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(months=2),
                    )
                ],
                [
                    (
                        self.user_employee,
                        self.reference_datetime - relativedelta(months=4),
                    )
                ],  # old logs but end of tone down
                [],  # no logs but end of town down
            ],
            [
                # daily
                ("daily", self.reference_datetime.date()),
                ("daily", self.reference_datetime.date()),
                ("daily", self.reference_datetime.date()),
                ("daily", self.reference_datetime.date()),
                # weekly
                ("weekly", self.reference_datetime.date()),
                ("weekly", self.reference_datetime.date()),
                ("weekly", self.reference_datetime.date()),
                # monthly
                ("monthly", self.reference_datetime.date()),
                ("monthly", self.reference_datetime.date()),
                ("monthly", self.reference_datetime.date()),
                # quarterly
                ("quarterly", self.reference_datetime.date()),
                ("quarterly", self.reference_datetime.date()),
                ("quarterly", self.reference_datetime.date()),
            ],
            [
                (
                    "daily",
                    self.reference_datetime.date() + relativedelta(days=1),
                    "Daily ok",
                ),  # just push date
                (
                    "daily",
                    self.reference_datetime.date() + relativedelta(days=1),
                    "Daily ok, 2 days - 1 hour",
                ),  # just push date
                (
                    "weekly",
                    self.reference_datetime.date() + relativedelta(weeks=1),
                    "Daily old logs (2 days + 1 hour)",
                ),  # tone down on daily
                (
                    "weekly",
                    self.reference_datetime.date() + relativedelta(weeks=1),
                    "Daily no logs",
                ),  # tone down on daily
                # weekly
                (
                    "weekly",
                    self.reference_datetime.date() + relativedelta(weeks=1),
                    "Weekly ok",
                ),  # just push date
                (
                    "monthly",
                    self.reference_datetime.date() + relativedelta(months=1),
                    "Weekly old logs",
                ),  # tone down on weekly
                (
                    "monthly",
                    self.reference_datetime.date() + relativedelta(months=1),
                    "Weekly no logs",
                ),  # tone down on weekly
                # monthly
                (
                    "monthly",
                    self.reference_datetime.date() + relativedelta(months=1),
                    "Monthly ok",
                ),  # just push date
                (
                    "quarterly",
                    self.reference_datetime.date() + relativedelta(months=3),
                    "Monthly old logs",
                ),  # tone down on monthly
                (
                    "quarterly",
                    self.reference_datetime.date() + relativedelta(months=3),
                    "Monthly no logs",
                ),  # tone down on monthly
                # quarterly
                (
                    "quarterly",
                    self.reference_datetime.date() + relativedelta(months=3),
                    "Quaterly ok",
                ),  # just push date
                (
                    "quarterly",
                    self.reference_datetime.date() + relativedelta(months=3),
                    "Quaterly ok",
                ),  # just push date
                (
                    "quarterly",
                    self.reference_datetime.date() + relativedelta(months=3),
                    "Quaterly ok",
                ),  # just push date
            ],
            strict=True,
        ):
            with self.subTest(
                logs=logs, msg=msg, periodicity=periodicity, run_date=run_date
            ):
                digest.write(
                    {
                        "next_run_date": run_date,
                        "periodicity": periodicity,
                    }
                )
                for log_user, log_dt in logs:
                    self._setup_logs_for_users(log_user, log_dt)

                with (
                    self.mock_datetime_and_now(self.reference_datetime),
                    self.mock_mail_gateway(),
                ):
                    digest.action_send()

                self.assertEqual(digest.next_run_date, exp_run_date)
                self.assertEqual(digest.periodicity, exp_periodicity)
                self.env["res.users.log"].with_user(SUPERUSER_ID).search([]).unlink()


@tagged("digest", "mail_mail", "-at_install", "post_install")
class TestUnsubscribe(MailCommon, HttpCaseWithUserDemo):
    def setUp(self):
        super().setUp()

        self.test_digest = self.env["digest.digest"].create(
            {
                "kpi_mail_message_total": True,
                "kpi_res_users_connected": True,
                "name": "My Digest",
                "periodicity": "daily",
                "user_ids": self.user_demo.ids,
            }
        )
        self.test_digest._action_subscribe_users(self.user_demo)
        self.base_url = self.test_digest.get_base_url()
        self.user_demo_unsubscribe_token = self.test_digest._get_unsubscribe_token(
            self.user_demo.id
        )

    def test_mail_mail_headers(self):
        """Test mail generated for digest contains unsubscribe headers"""
        digest = self.env["digest.digest"].browse(self.test_digest.ids)
        digest._action_subscribe_users(self.user_employee)

        with self.mock_mail_gateway():
            digest.action_send()

        # find outgoing mail, click on unsubscribe link
        for user in self.user_employee + self.user_demo:
            mail = self._find_mail_mail_wemail(user.email_formatted, "outgoing")
            headers = mail.headers  # fields.Json: already a dict
            unsubscribe_url = headers.get("List-Unsubscribe", "").strip("<>")
            self.assertTrue(unsubscribe_url)
            self.url_open(unsubscribe_url, method="POST")

        self.assertFalse(
            digest.user_ids, "Users should have been unsubscribed from digest"
        )

    def test_unsubscribe(self):
        """Test various combination of unsubscribe: logged, using token, ..."""
        digest = self.test_digest
        demo_token = digest._get_unsubscribe_token(self.user_demo.id)
        for test_user, is_member, is_logged, token, exp_code in [
            (self.user_demo, True, True, False, 200),  # unsubscribe logged, easy
            (
                self.user_demo,
                False,
                True,
                False,
                200,
            ),  # unsubscribe not a member should not crash
            (
                self.user_demo,
                False,
                False,
                demo_token,
                200,
            ),  # unsubscribe using a token
            (
                self.user_demo,
                False,
                False,
                "probably-not-a-token",
                404,
            ),  # wrong token -> crash
            (
                self.user_demo,
                False,
                False,
                False,
                404,
            ),  # cannot be done unlogged / no token
        ]:
            with self.subTest(
                user_name=test_user.name,
                is_member=is_member,
                is_logged=is_logged,
                token=token,
            ):
                if is_member:
                    digest._action_subscribe_users(test_user)
                    self.assertIn(test_user, digest.user_ids)
                else:
                    digest._action_unsubscribe_users(test_user)
                    self.assertNotIn(test_user, digest.user_ids)

                self.authenticate(
                    test_user.login if is_logged else None,
                    test_user.login if is_logged else None,
                )
                if token:
                    response = self._url_unsubscribe(token=token, user_id=test_user.id)
                else:
                    response = self._url_unsubscribe()
                self.assertEqual(response.status_code, exp_code)
                self.assertNotIn(test_user, digest.user_ids)

    def test_unsubscribe_token_one_click(self):
        """Test one-click: should be ok with POST, not GET to avoid link crawling"""
        self.assertIn(self.user_demo, self.test_digest.user_ids)
        self.authenticate(None, None)

        with mute_logger("odoo.addons.http_routing.models.ir_http"):
            # Ensure we cannot unregister using GET method (method not allowed)
            response = self._url_unsubscribe(
                token=self.user_demo_unsubscribe_token,
                user_id=self.user_demo.id,
                one_click="1",
                method="GET",
            )
        self.assertEqual(response.status_code, 405, "GET method is not allowed")
        self.assertIn(self.user_demo, self.test_digest.user_ids)

        # Ensure we can unregister with POST method
        response = self._url_unsubscribe(
            token=self.user_demo_unsubscribe_token,
            user_id=self.user_demo.id,
            one_click="1",
            method="POST",
        )
        self.assertEqual(
            response.status_code,
            200,
            "Valid one-click unsubscribe just returns an OK 200",
        )
        self.assertNotIn(self.user_demo, self.test_digest.user_ids)

    def _url_unsubscribe(self, token=None, user_id=None, one_click=None, method="GET"):
        url_params = {}
        if token is not None:
            url_params["token"] = token
        if user_id is not None:
            url_params["user_id"] = user_id
        if one_click is not None:
            unsubscribe_route = "unsubscribe_oneclick"
        else:
            unsubscribe_route = "unsubscribe"

        url = urls.urljoin(
            self.base_url,
            f"digest/{self.test_digest.id}/{unsubscribe_route}?{urlencode(url_params)}",
        )
        return self.url_open(url, timeout=10, allow_redirects=True, method=method)


@tagged("digest")
class TestDigestDefects(TestDigestCommon):
    """One test per defect the 2026-08 audit of this module fixed.

    Each was written against the code before the fix and observed to fail
    there; a regression test that passes on the broken code is worth nothing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.calendar_tz = "America/Mexico_City"  # UTC-6, never UTC, never +0 in DST
        cls.company_1.resource_calendar_id.tz = cls.calendar_tz
        cls.env["mail.message"].search(
            [
                ("subtype_id", "=", cls.env.ref("mail.mt_comment").id),
                ("message_type", "in", ("comment", "email", "email_outgoing")),
            ]
        ).unlink()
        cls._setup_messages()  # 3 in the last 24h, 8 in the last week, 15 in the month

    # ------------------------------------------------------------
    # TIME WINDOWS
    # ------------------------------------------------------------

    @users("admin")
    def test_timeframes_are_naive_utc(self):
        """The window bounds land in a domain against naive-UTC columns.

        They used to be returned in the company calendar's timezone and
        serialized with ``strftime``, which does not convert: a UTC-6 company
        asked for everything up to six hours ago and called it "last 24 hours".
        """
        digest = self.digest_1.with_user(self.env.user)
        now = datetime.now(UTC).replace(tzinfo=None)
        timeframes = digest._get_timeframes(self.company_1)

        self.assertEqual(len(timeframes), 3)
        for label, (current, previous) in timeframes:
            for bound in (*current, *previous):
                self.assertIsNone(
                    bound.tzinfo,
                    f"{label}: bounds reach Datetime.to_string(), which never converts",
                )
            self.assertLess(
                abs((current[1] - now).total_seconds()),
                60,
                f"{label}: the current window must end now, not {self.calendar_tz} now",
            )
            self.assertEqual(
                current[0],
                previous[1],
                f"{label}: the previous window must end where the current one starts",
            )

    @users("admin")
    def test_timeframe_bounds_reach_the_domain_unshifted(self):
        """End-to-end: the tz of the company calendar must not move a KPI count.

        Posted at a fixed offset rather than relying on the random spread
        `_setup_messages` lays down: a six-hour shift that happens to keep the
        same three messages proves nothing.
        """
        digest = self.digest_1.with_user(self.env.user)
        self.env["mail.message"].search(
            [
                ("subtype_id", "=", self.env.ref("mail.mt_comment").id),
                ("message_type", "in", ("comment", "email", "email_outgoing")),
            ]
        ).unlink()
        now = fields.Datetime.now()
        for hours_ago in (2, 5, 20, 26):  # the last is outside the 24h window
            self.partner_admin.message_post(
                author_id=self.partner_admin.id,
                body=f"{hours_ago}h ago",
                message_type="comment",
                subtype_xmlid="mail.mt_comment",
                create_date=now - relativedelta(hours=hours_ago),
            )
        self.env.flush_all()

        _label, (current, __) = digest._get_timeframes(self.company_1)[0]
        start, end, __ = digest.with_context(
            start_datetime=current[0],
            end_datetime=current[1],
        )._get_kpi_compute_parameters()

        self.assertEqual(
            digest._get_kpi_value(
                "kpi_mail_message_total_value",
                current,
                self.company_1,
                self.env.user,
            ),
            3,
            f"window {start} .. {end} must be the real last 24 hours",
        )

    # ------------------------------------------------------------
    # MARGINS
    # ------------------------------------------------------------

    @users("admin")
    def test_margin_reports_a_fall_to_zero(self):
        """A KPI that collapsed to nothing is a plain -100%, and the old guard
        was the reason it showed no badge at all. Growth FROM zero stays
        badge-less on purpose: it has no percentage, and
        `account._get_column_percent_comparison_data` answers the
        same case with a muted n/a rather than a made-up figure."""
        digest = self.digest_1.with_user(self.env.user)
        for value, previous, expected in [
            (0, 0, 0.0),
            (10, 10, 0.0),
            (0, 10, -100.0),  # was 0.0: no badge at all on a collapse
            (10, 0, 0.0),  # no basis to compare against -> no badge
            (-5, 0, 0.0),
            (10, 5, 100.0),
            (5, 10, -50.0),
            (1, 3, -66.67),
            # A negative base inverts the sign: -5 -> -10 is a fall that reads
            # as +100%. Recorded, not fixed -- account_reports hits the same
            # trap and answers it in the DISPLAY layer (it flips the colour),
            # and no digest KPI is expected to be negative often enough to
            # justify changing the number here.
            (-10, -5, 100.0),
        ]:
            with self.subTest(value=value, previous=previous):
                self.assertEqual(digest._get_margin_value(value, previous), expected)

    # ------------------------------------------------------------
    # TIPS
    # ------------------------------------------------------------

    @users("admin")
    def test_tips_are_consumed_one_by_one(self):
        """`tips.user_ids += user` wrote the UNION of every selected tip's
        audience back onto each of them, so with tips_count > 1 a tip acquired
        the audience of the tips beside it and was never offered to them."""
        Tip = self.env["digest.tip"].sudo()
        # the tips shipped as data all sort ahead of anything created here
        Tip.search([]).unlink()
        tip_a, tip_b = Tip.create(
            [
                {
                    "name": "Tip A",
                    "sequence": 1,
                    "tip_description": "<p>A</p>",
                    "user_ids": [Command.link(self.user_admin.id)],
                },
                {
                    "name": "Tip B",
                    "sequence": 2,
                    "tip_description": "<p>B</p>",
                    "user_ids": [Command.link(self.user_employee.id)],
                },
            ]
        )
        reader = self.env["res.users"].create(
            {
                "name": "Tip Reader",
                "login": "digest_tip_reader",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

        self.digest_1.with_user(self.env.user)._get_tips(
            self.company_1,
            reader,
            tips_count=2,
            consumed=True,
        )

        self.assertEqual(
            tip_a.user_ids,
            self.user_admin + reader,
            "Tip A must gain the reader and nothing else",
        )
        self.assertEqual(
            tip_b.user_ids,
            self.user_employee + reader,
            "Tip B must gain the reader and nothing else",
        )

    # ------------------------------------------------------------
    # CACHING
    # ------------------------------------------------------------

    def test_is_subscribed_is_the_reader_s_own(self):
        """Without depends_context('uid') a non-stored compute has ONE cache
        entry per record for the transaction, so `_action_send`'s per-recipient
        read handed the first recipient's answer to everybody after them."""
        digest = self.digest_1
        digest._action_subscribe_users(self.user_admin)
        digest._action_unsubscribe_users(self.user_employee)

        self.assertTrue(digest.with_user(self.user_admin).is_subscribed)
        self.assertFalse(
            digest.with_user(self.user_employee).is_subscribed,
            "the employee is not a recipient, whoever read the field first",
        )
        # and back the other way, so the test cannot pass on read order alone
        self.assertTrue(digest.with_user(self.user_admin).is_subscribed)

    @users("admin")
    def test_reading_one_digest_s_kpi_keeps_the_others_warm(self):
        """`invalidate_model` dropped the KPI values of every digest.digest in
        the transaction -- in a cron pass, every digest already computed."""
        digest = self.digest_1.with_user(self.env.user)
        others = self.env["digest.digest"].create(
            [
                {"name": f"Bystander {i}", "kpi_mail_message_total": True}
                for i in range(5)
            ]
        )
        window = digest._get_timeframes(self.company_1)[0][1][0]
        warm = others.with_context(start_datetime=window[0], end_datetime=window[1])
        warm.mapped("kpi_mail_message_total_value")

        with self.assertQueryCount(0):
            warm.mapped("kpi_mail_message_total_value")

        digest._get_kpi_value(
            "kpi_mail_message_total_value",
            window,
            self.company_1,
            self.env.user,
        )

        with self.assertQueryCount(0):
            warm.mapped("kpi_mail_message_total_value")

    @users("admin")
    def test_a_denied_kpi_is_resolved_once_not_once_per_column(self):
        """The AccessError skip lived inside the column loop, so a KPI the
        recipient may not read was recomputed in every one of the three
        columns to reach the same refusal three times over."""
        digest = self.digest_1.with_user(self.env.user)
        calls = []
        denied = AccessError("nope")

        def _refuse(records):
            calls.append(records)
            raise denied

        with patch.object(
            type(digest),
            "_compute_kpi_mail_message_total_value",
            _refuse,
        ):
            kpi_data = digest._get_kpi_data(self.company_1, self.user_admin)

        # Two, not one: `_run_batch_then_single` retries a compute that raised on
        # the whole recordset once more per record, which is the ORM's own
        # behaviour and not something this module decides. Three columns used
        # to ask, so six.
        self.assertEqual(len(calls), 2, "one column asks, the ORM retries once")
        self.assertNotIn(
            "kpi_mail_message_total",
            [kpi["kpi_name"] for kpi in kpi_data],
            "a KPI the reader cannot see stays out of their mail",
        )

    # ------------------------------------------------------------
    # SLOWDOWN
    # ------------------------------------------------------------

    @users("admin")
    def test_one_scan_answers_every_window_with_the_same_numbers(self):
        """The six windows now come from one filtered aggregate instead of six
        range aggregates. This is the differential that says so: every KPI, read
        both ways, must agree digit for digit."""
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        digest.write(dict.fromkeys(digest._get_kpi_boolean_names(), True))
        self.env.flush_all()

        batched = digest._get_kpi_data(self.company_1, self.user_admin)

        # the fallback path: no window list in the context, so every read is a
        # single-window `_read_group`, exactly as before this change
        original = type(digest)._read_kpi_over_windows
        try:
            type(digest)._read_kpi_over_windows = lambda *a, **kw: None
            per_window = digest._get_kpi_data(self.company_1, self.user_admin)
        finally:
            type(digest)._read_kpi_over_windows = original

        self.assertTrue(batched, "the digest must render at least one KPI")
        self.assertEqual(
            [kpi["kpi_name"] for kpi in batched],
            [kpi["kpi_name"] for kpi in per_window],
        )
        for one, six in zip(batched, per_window, strict=True):
            for col in ("kpi_col1", "kpi_col2", "kpi_col3"):
                with self.subTest(kpi=one["kpi_name"], col=col):
                    self.assertEqual(one[col], six[col])

    @users("admin")
    def test_one_scan_is_one_query_and_six_answers(self):
        """Measured on the mechanism, not through a KPI: with only `digest`
        installed, neither shipped KPI takes the fast path --
        `kpi_mail_message_total` never calls the helper, and
        `res.users.login_date` is not stored. The eight KPIs that do take it all
        come from other addons (crm x2, hr_recruitment, point_of_sale, project,
        sale, website_sale, helpdesk)."""
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        windows = tuple(
            (fields.Datetime.to_string(s), fields.Datetime.to_string(e))
            for __, pair in digest._get_timeframes(self.company_1)
            for s, e in pair
        )
        scoped = digest.with_context(digest_windows=windows)
        memo = {}
        self.cr.cache[KPI_AGGREGATE_MEMO] = memo
        try:
            # warm AFTER invalidating: record-rule resolution is a query of its
            # own, it is shared across every KPI in the render, and measuring it
            # here would be measuring the wrong thing.
            self.env.invalidate_all()
            scoped._read_kpi_over_windows(
                "kpi_warm",
                "res.users",
                "create_date",
                Domain.TRUE,
                None,
                self.company_1,
            )
            before = self.cr.sql_statement_count
            one_scan = scoped._read_kpi_over_windows(
                "kpi_probe",
                "res.users",
                "create_date",
                Domain.TRUE,
                None,
                self.company_1,
            )
            spent = self.cr.sql_statement_count - before
        finally:
            self.cr.cache.pop(KPI_AGGREGATE_MEMO, None)

        self.assertEqual(spent, 1, "six windows, one query")
        per_company = one_scan[self.company_1.id]
        self.assertEqual(len(per_company), 6, "and six answers out of it")

        # the same six numbers the per-window path would have produced
        expected = []
        for start, end in windows:
            rows = self.env["res.users"]._read_group(
                domain=Domain(
                    [
                        ("company_id", "in", self.company_1.ids),
                        ("create_date", ">=", start),
                        ("create_date", "<", end),
                    ]
                ),
                groupby=["company_id"],
                aggregates=["__count"],
            )
            expected.append({c.id: n for c, n in rows}.get(self.company_1.id, 0))
        self.assertEqual([per_company[w] for w in windows], expected)

    @users("admin")
    def test_one_scan_sees_a_sum_the_ORM_has_not_written_yet(self):
        """The aggregate is raw SQL, so it has to flush first.

        `_search` already flushes the fields in the DOMAIN, which is why a count
        over `create_date` looks fine either way -- the first draft of this test
        used one and passed against the unflushed version too. The summed field
        is not in the domain, so it is the one that exposes the difference:
        `env.execute_query` flushes it, `cr.execute` would read the old row.
        """
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        calendar = self.company_1.resource_calendar_id
        self.assertTrue(self.env["resource.calendar"]._fields["hours_per_day"].store)
        window = ("2000-01-01 00:00:00", "2100-01-01 00:00:00")

        def summed():
            self.cr.cache[KPI_AGGREGATE_MEMO] = {}
            try:
                out = digest.with_context(
                    digest_windows=(window,)
                )._read_kpi_over_windows(
                    "kpi_flush_probe",
                    "resource.calendar",
                    "create_date",
                    Domain([("id", "=", calendar.id)]),
                    "hours_per_day",
                    self.company_1,
                )
            finally:
                self.cr.cache.pop(KPI_AGGREGATE_MEMO, None)
            return out.get(self.company_1.id, {}).get(window, 0)

        self.env.flush_all()
        self.assertEqual(summed(), calendar.hours_per_day)

        calendar.hours_per_day = 99.0  # deliberately NOT flushed
        self.cr.execute(
            "SELECT hours_per_day FROM resource_calendar WHERE id = %s", (calendar.id,)
        )
        self.assertNotEqual(self.cr.fetchone()[0], 99.0, "the row is still stale")
        self.assertEqual(summed(), 99.0, "the scan must flush before it reads")

    @users("admin")
    def test_a_non_stored_date_field_takes_the_slow_path(self):
        """`res.users.login_date` is a non-stored related through a One2many;
        `_field_to_sql` cannot express it and the helper must decline rather
        than raise. This is the module's own KPI, so the guard is load-bearing."""
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        self.assertFalse(self.env["res.users"]._fields["login_date"].store)
        windows = tuple(
            (fields.Datetime.to_string(s), fields.Datetime.to_string(e))
            for __, pair in digest._get_timeframes(self.company_1)
            for s, e in pair
        )
        self.cr.cache[KPI_AGGREGATE_MEMO] = {}
        try:
            declined = digest.with_context(
                digest_windows=windows
            )._read_kpi_over_windows(
                "kpi_res_users_connected_value",
                "res.users",
                "login_date",
                Domain.TRUE,
                None,
                self.company_1,
            )
        finally:
            self.cr.cache.pop(KPI_AGGREGATE_MEMO, None)
        self.assertIsNone(declined, "declined, not raised")

        # and the KPI still reads correctly through the fallback
        self.env["res.users"].with_user(self.user_employee)._update_last_login()
        self.all_digests.invalidate_recordset()
        self.assertEqual(self.digest_1.kpi_res_users_connected_value, 1)

    @users("admin")
    def test_the_memo_cannot_serve_one_kpi_s_answer_to_another(self):
        """Two KPIs over the same model with different domains must not share a
        memo entry. The key is the KPI field, which is unique per KPI."""
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        windows = tuple(
            (fields.Datetime.to_string(s), fields.Datetime.to_string(e))
            for __, pair in digest._get_timeframes(self.company_1)
            for s, e in pair
        )
        memo = {}
        self.cr.cache[KPI_AGGREGATE_MEMO] = memo
        try:
            scoped = digest.with_context(digest_windows=windows)
            everything = scoped._read_kpi_over_windows(
                "kpi_a", "res.users", "create_date", Domain.TRUE, None, self.company_1
            )
            nothing = scoped._read_kpi_over_windows(
                "kpi_b",
                "res.users",
                "create_date",
                Domain([("login", "=", "__nobody__")]),
                None,
                self.company_1,
            )
        finally:
            self.cr.cache.pop(KPI_AGGREGATE_MEMO, None)

        self.assertEqual(len(memo), 2, "two KPIs, two memo entries")
        self.assertNotEqual(
            everything,
            nothing,
            "the impossible domain must not read the other KPI back",
        )
        self.assertFalse(any(nothing.values()), "nothing matches that domain")

    @users("admin")
    def test_the_memo_does_not_outlive_the_render(self):
        digest = self.env["digest.digest"].browse(self.digest_1.ids)
        digest._get_kpi_data(self.company_1, self.user_admin)
        self.assertNotIn(
            KPI_AGGREGATE_MEMO,
            self.cr.cache,
            "a memo left on the cursor would answer the next recipient",
        )

    @users("admin")
    def test_slowdown_costs_one_read_group_whatever_the_batch(self):
        """One `search_count` per digest made the cron linear in the number of
        digests. Measured as a marginal cost between two batch sizes so a warm
        cache cannot make the assertion vacuous."""
        Digest = self.env["digest.digest"]

        def measure(count):
            digests = Digest.create(
                [
                    {
                        "name": f"Slowdown {count}-{i}",
                        "periodicity": "daily",
                        "user_ids": [Command.link(self.user_employee.id)],
                    }
                    for i in range(count)
                ]
            )
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.cr.sql_statement_count
            digests._get_digests_to_slowdown()
            return self.cr.sql_statement_count - before

        small, large = measure(2), measure(20)
        self.assertLessEqual(
            large - small,
            2,
            f"18 further digests cost {large - small} extra queries; the log "
            f"lookup is one _read_group for the whole recordset",
        )

    @users("admin")
    def test_slowdown_still_reads_the_recipients_logs(self):
        """The batched form must keep the answer the per-digest one gave."""
        Digest = self.env["digest.digest"]
        Log = self.env["res.users.log"].with_user(SUPERUSER_ID)
        Log.search([]).unlink()

        awake, asleep, empty = Digest.create(
            [
                {
                    "name": "Awake",
                    "periodicity": "daily",
                    "user_ids": [Command.link(self.user_employee.id)],
                },
                {
                    "name": "Asleep",
                    "periodicity": "daily",
                    "user_ids": [Command.link(self.user_admin.id)],
                },
                {"name": "No recipients", "periodicity": "daily"},
            ]
        )
        Log.create({"create_uid": self.user_employee.id})
        self.env.flush_all()

        to_slowdown = (awake + asleep + empty)._get_digests_to_slowdown()
        self.assertEqual(to_slowdown, asleep + empty)

    # ------------------------------------------------------------
    # CONFIGURATION
    # ------------------------------------------------------------

    def test_periodicity_table_is_the_selection(self):
        """The field's selection is built from the table, so they cannot
        disagree. What is still worth holding is the table's own shape: a
        fallback that is not itself a key would raise mid-send, and a
        `quarterly` that fell back to something else would never terminate."""
        selection = self.env["digest.digest"]._fields["periodicity"].selection
        self.assertEqual(
            [value for value, __ in selection],
            list(PERIODICITIES),
            "the selection is PERIODICITY_SELECTION; an override would be a copy",
        )
        for name, periodicity in PERIODICITIES.items():
            with self.subTest(periodicity=name):
                self.assertIn(periodicity.slower, PERIODICITIES)
                self.assertTrue(periodicity.label)
        self.assertEqual(
            PERIODICITIES["quarterly"].slower,
            "quarterly",
            "quarterly is the floor: there is nothing slower to fall back to",
        )

    def test_get_next_periodicity_covers_every_slower_target(self):
        """`_get_next_periodicity` used to look up its label in a second,
        hand-written dict keyed by the three `slower` values the table
        happens to produce today. A `PERIODICITIES` entry whose `slower`
        isn't one of those hardcoded keys passed
        `test_periodicity_table_is_the_selection` in full and only raised
        here, on the next slowed-down digest send. Exercise every non-floor
        entry so the next added periodicity is caught by a test, not a
        live cron."""
        digest = self.env["digest.digest"].create(
            {"name": "Test", "periodicity": "daily"}
        )
        for name, periodicity in PERIODICITIES.items():
            if name == periodicity.slower:  # the floor has nowhere to slow down to
                continue
            with self.subTest(periodicity=name):
                digest.periodicity = name
                slower, label = digest._get_next_periodicity()
                self.assertEqual(slower, periodicity.slower)
                self.assertTrue(label)

    def test_auto_subscription_honours_the_unticked_setting(self):
        """res.config.settings stores a Boolean config_parameter as the STRING
        'False', which is truthy: every user created after Digest Emails was
        switched off went on being subscribed anyway."""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("digest.default_digest_emails", "False")
        icp.set_param("digest.default_digest_id", str(self.digest_1.id))

        user = self.env["res.users"].create(
            {
                "name": "Unsubscribed By Default",
                "login": "digest_setting_off",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        self.assertNotIn(user, self.digest_1.user_ids)

        icp.set_param("digest.default_digest_emails", "True")
        subscribed = self.env["res.users"].create(
            {
                "name": "Subscribed By Default",
                "login": "digest_setting_on",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        self.assertIn(subscribed, self.digest_1.user_ids)

    def test_auto_subscription_survives_a_broken_parameter(self):
        """A hand-edited parameter must not break every res.users creation."""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("digest.default_digest_emails", "True")
        icp.set_param("digest.default_digest_id", "not-an-id")

        user = self.env["res.users"].create(
            {
                "name": "Created Anyway",
                "login": "digest_bad_param",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )
        self.assertTrue(user.id)

    @users("admin")
    def test_create_rejects_a_bad_periodicity_the_ORM_s_way(self):
        """Seeding the run date reads PERIODICITIES before super() ever sees the
        values. Indexing it there answered a bad Selection with a bare
        `KeyError: 'hourly'` instead of the ORM error that names the field."""
        with self.assertRaises(ValueError) as caught:
            self.env["digest.digest"].create({"name": "Bad", "periodicity": "hourly"})
        self.assertNotIsInstance(caught.exception, KeyError)
        self.assertIn("hourly", str(caught.exception))

    @users("admin")
    def test_log_attribution_sticks_whatever_the_test_phase(self):
        """`create_uid` in create() values survives only while the registry is
        loading. Every tone-down assertion in this module rests on the helper
        that sets it, and post_install it silently lands on `__system__`."""
        logs = self._setup_logs_for_users(
            self.user_employee + self.user_admin,
            datetime(2024, 2, 13, 13, 30, 0),
        )
        self.assertEqual(logs.create_uid, self.user_employee + self.user_admin)

    def test_cron_sends_every_due_digest_and_leaves_the_rest(self):
        """`_cron_send_digest_email` had no test at all, and now commits between
        batches, so it needs `_commit_progress` patched like every other cron."""
        Digest = self.env["digest.digest"]
        Digest.search([]).write({"state": "deactivated"})
        today = fields.Date.today()
        due, not_yet, deactivated = Digest.create(
            [
                {
                    "name": "Due",
                    "next_run_date": today,
                    "user_ids": [Command.link(self.user_employee.id)],
                },
                {
                    "name": "Not yet",
                    "next_run_date": today + relativedelta(days=3),
                    "user_ids": [Command.link(self.user_employee.id)],
                },
                {
                    "name": "Deactivated",
                    "next_run_date": today,
                    "user_ids": [Command.link(self.user_employee.id)],
                },
            ]
        )
        deactivated.action_deactivate()
        self._setup_logs_for_users(self.user_employee, fields.Datetime.now())
        self.env.flush_all()

        budget = []

        def _commit_progress(cron, processed=0, *, remaining=None, deactivate=False):
            budget.append((processed, remaining))
            return float("inf")  # never commits: a test cursor forbids it

        with (
            patch.object(
                type(self.env["ir.cron"]), "_commit_progress", _commit_progress
            ),
            self.mock_mail_gateway(),
        ):
            Digest._cron_send_digest_email()

        self.assertEqual(
            len(self._new_mails), 1, "only the due, activated digest sends"
        )
        self.assertEqual(self._new_mails.email_to, self.user_employee.email_formatted)
        self.assertEqual(budget[0], (0, 1), "the total is announced once, and it is 1")
        self.assertEqual(due.next_run_date, today + relativedelta(days=1))
        self.assertEqual(
            not_yet.next_run_date,
            today + relativedelta(days=3),
            "a digest that is not due is not touched",
        )
        self.assertEqual(deactivated.next_run_date, today)

    def test_cron_stops_when_the_budget_runs_out(self):
        Digest = self.env["digest.digest"]
        Digest.search([]).write({"state": "deactivated"})
        today = fields.Date.today()
        digests = Digest.create(
            [{"name": f"Batch {i}", "next_run_date": today} for i in range(25)]
        )
        self.env.flush_all()
        calls = []

        def _commit_progress(cron, processed=0, *, remaining=None, deactivate=False):
            calls.append(processed)
            # call 1 is the `remaining=` announcement, before any batch runs;
            # the deadline lands after the second batch reports.
            return 0.0 if len(calls) >= 3 else float("inf")

        with (
            patch.object(
                type(self.env["ir.cron"]), "_commit_progress", _commit_progress
            ),
            self.mock_mail_gateway(),
        ):
            Digest._cron_send_digest_email()

        moved = digests.filtered(lambda d: d.next_run_date != today)
        self.assertEqual(len(moved), 20, "two batches of ten ran, then it gave up")
        self.assertEqual(
            len(digests) - len(moved),
            5,
            "the five left over are still due on the next pass, not skipped",
        )

    def test_a_broken_kpi_does_not_abort_the_whole_batch(self):
        """A KPI compute can be arbitrary Studio-authored logic. Only
        `AccessError` was ever caught around it, so any other exception used
        to propagate out of `_action_send`'s whole loop over `self` -- taking
        down every other digest sharing that same uncommitted cron batch,
        alphabetically-first digest included."""
        Digest = self.env["digest.digest"]
        Digest.search([]).write({"state": "deactivated"})
        today = fields.Date.today()
        bad, good = Digest.create(
            [
                {
                    "name": "Bad Digest (broken KPI)",
                    "next_run_date": today,
                    "periodicity": "daily",
                    "kpi_res_users_connected": True,
                    "user_ids": [Command.link(self.user_employee.id)],
                },
                {
                    "name": "Good Digest",
                    "next_run_date": today,
                    "periodicity": "daily",
                    "user_ids": [Command.link(self.user_employee.id)],
                },
            ]
        )
        # a recipient with no recent log gets slowed down (periodicity bumped
        # to weekly) regardless of this test's fix -- give them one so the
        # only thing under test is the batch-isolation behaviour.
        self._setup_logs_for_users(self.user_employee, fields.Datetime.now())
        self.env.flush_all()

        def _raise(records):
            raise ZeroDivisionError("broken KPI formula")

        with (
            patch.object(type(bad), "_compute_kpi_res_users_connected_value", _raise),
            self.mock_mail_gateway(),
        ):
            (bad + good).action_send()

        self.assertEqual(len(self._new_mails), 1, "the good digest still gets its mail")
        self.assertEqual(self._new_mails.email_to, self.user_employee.email_formatted)
        self.assertEqual(
            bad.next_run_date,
            today + relativedelta(days=1),
            "the broken digest is still rescheduled, not stuck retrying forever",
        )
        self.assertEqual(good.next_run_date, today + relativedelta(days=1))

    @users("admin")
    def test_create_seeds_the_run_date_without_a_second_write(self):
        digests = self.env["digest.digest"].create(
            [
                {"name": "Seeded daily", "periodicity": "daily"},
                {"name": "Seeded quarterly", "periodicity": "quarterly"},
                {"name": "Seeded default"},
                {"name": "Explicit", "next_run_date": date(2030, 1, 1)},
            ]
        )
        today = fields.Date.today()
        self.assertEqual(digests[0].next_run_date, today + relativedelta(days=1))
        self.assertEqual(
            digests[1].next_run_date,
            today + relativedelta(months=3),
            "quarterly had no branch of its own, only a bare else",
        )
        self.assertEqual(digests[2].next_run_date, today + relativedelta(days=1))
        self.assertEqual(
            digests[3].next_run_date,
            date(2030, 1, 1),
            "an explicit date is never overwritten",
        )


@tagged("digest", "-at_install", "post_install")
class TestUnsubscribeRoutes(MailCommon, HttpCaseWithUserDemo):
    def test_both_spellings_of_the_one_click_route_answer(self):
        """The header of every digest already in a mailbox carries the old
        misspelling, and those keep arriving."""
        for route, user in [
            ("unsubscribe_oneclik", self.user_demo),
            ("unsubscribe_oneclick", self.user_employee),
        ]:
            with self.subTest(route=route):
                digest = self.env["digest.digest"].create(
                    {
                        "name": "Route Digest",
                        "user_ids": user.ids,
                    }
                )
                token = digest._get_unsubscribe_token(user.id)
                url = urls.urljoin(
                    digest.get_base_url(),
                    f"digest/{digest.id}/{route}?{urlencode({'token': token, 'user_id': user.id})}",
                )
                response = self.url_open(url, method="POST", timeout=10)
                self.assertEqual(response.status_code, 200)
                self.assertNotIn(user, digest.user_ids)

    def test_set_periodicity_refuses_what_the_field_refuses(self):
        digest = self.env["digest.digest"].create({"name": "Periodicity Digest"})
        self.authenticate("admin", "admin")
        base = digest.get_base_url()

        with mute_logger("odoo.addons.http_routing.models.ir_http"):
            response = self.url_open(
                urls.urljoin(
                    base, f"digest/{digest.id}/set_periodicity?periodicity=hourly"
                ),
                timeout=10,
            )
        self.assertEqual(
            response.status_code, 404, "not a 500 out of a bare ValueError"
        )
        self.assertEqual(digest.periodicity, "daily")

        response = self.url_open(
            urls.urljoin(
                base, f"digest/{digest.id}/set_periodicity?periodicity=weekly"
            ),
            timeout=10,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(digest.periodicity, "weekly")

    def test_set_periodicity_on_a_deleted_digest_is_a_404(self):
        digest = self.env["digest.digest"].create({"name": "Doomed"})
        digest_id, base_url = digest.id, digest.get_base_url()
        digest.unlink()
        self.authenticate("admin", "admin")

        with mute_logger("odoo.addons.http_routing.models.ir_http"):
            response = self.url_open(
                urls.urljoin(
                    base_url, f"digest/{digest_id}/set_periodicity?periodicity=weekly"
                ),
                timeout=10,
            )
        self.assertEqual(
            response.status_code,
            404,
            "it used to redirect to /odoo/digest.digest/False",
        )
