import base64
import datetime
from unittest.mock import patch

from freezegun import freeze_time
from markupsafe import Markup

from odoo.exceptions import ValidationError
from odoo.tests import tagged, users, warmup
from odoo.tools import mute_logger, safe_eval

from odoo.addons.mail.models.mail_template import (
    ATTACHMENT_FIELD_NAMES,
    DYNAMIC_FIELD_NAMES,
    RECIPIENT_FIELD_NAMES,
    SEND_RENDER_FIELDS,
    TEMPLATE_SPECIFIC_FIELD_NAMES,
)
from odoo.addons.mail.tests.common import MailCommon
from odoo.addons.mail.wizards.mail_compose_message import (
    COMPOSER_FIELD_TO_TEMPLATE_FIELD,
    TEMPLATE_FIELD_TO_COMPOSER_FIELD,
    TEMPLATE_RENDER_FIELDS,
)
from odoo.addons.test_mail.tests.common import TestRecipients


class TestMailTemplateCommon(MailCommon, TestRecipients):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_record = (
            cls.env["mail.test.lang"]
            .with_context(cls._test_context)
            .create(
                {
                    "email_from": "ignasse@example.com",
                    "name": "Test",
                }
            )
        )

        cls._attachments = [
            {
                "name": "first.txt",
                "datas": base64.b64encode(b"My first attachment"),
                "res_model": "res.partner",
                "res_id": cls.user_admin.partner_id.id,
            },
            {
                "name": "second.txt",
                "datas": base64.b64encode(b"My second attachment"),
                "res_model": "res.partner",
                "res_id": cls.user_admin.partner_id.id,
            },
        ]

        cls.email_1 = "test1@example.com"
        cls.email_2 = "test2@example.com"
        cls.email_3 = cls.partner_1.email

        # create a complete test template
        cls.test_template = cls._create_template(
            "mail.test.lang",
            {
                "attachment_ids": [
                    (0, 0, cls._attachments[0]),
                    (0, 0, cls._attachments[1]),
                ],
                "body_html": '<p>EnglishBody for <t t-out="object.name"/></p>',
                "lang": "{{ object.customer_id.lang or object.lang }}",
                "email_to": "%s, %s" % (cls.email_1, cls.email_2),
                "email_cc": "%s" % cls.email_3,
                "partner_to": "%s,%s"
                % (cls.partner_2.id, cls.user_admin.partner_id.id),
                "subject": "EnglishSubject for {{ object.name }}",
                "use_default_to": False,
            },
        )

        # activate translations
        cls._activate_multi_lang(
            layout_arch_db='<body><t t-out="message.body"/> English Layout for <t t-esc="model_description"/></body>',
            test_record=cls.test_record,
            test_template=cls.test_template,
        )

        # admin should receive emails
        cls.user_admin.write({"notification_type": "email"})
        # Force the attachments of the template to be in the natural order.
        cls.test_template.invalidate_recordset(["attachment_ids"])

        # dynamic reports
        cls.test_report = cls.env["ir.actions.report"].create(
            [
                {
                    "name": "Test Report 3 with variable data on Mail Test Ticket",
                    "model": "mail.test.ticket.mc",
                    "print_report_name": "'TestReport3 for %s' % object.name",
                    "report_type": "qweb-pdf",
                    "report_name": "test_mail.mail_test_ticket_test_variable_template",
                },
            ]
        )


@tagged("mail_template")
class TestMailTemplate(TestMailTemplateCommon):
    def test_template_add_context_action(self):
        self.test_template.create_action()

        # check template act_window has been updated
        self.assertTrue(bool(self.test_template.ref_ir_act_window))

        # check those records
        action = self.test_template.ref_ir_act_window
        self.assertEqual(action.name, "Send Mail (%s)" % self.test_template.name)
        self.assertEqual(action.binding_model_id.model, "mail.test.lang")

    def test_template_fields(self):
        """Test computed fields"""
        # has_dynamic_reports: based on ir.actions.report
        test_template_lang = self.test_template.with_user(self.user_employee)
        self.assertFalse(test_template_lang.has_dynamic_reports)
        test_template_ticket_mc = (
            self.env["mail.template"]
            .with_user(self.user_employee)
            .create(
                {
                    "model_id": self.env["ir.model"]._get_id("mail.test.ticket.mc"),
                }
            )
        )
        self.assertTrue(test_template_ticket_mc.has_dynamic_reports)
        # has_mail_server: based on ir.mail_server available
        self.assertTrue(test_template_lang.has_mail_server)
        self.assertTrue(test_template_ticket_mc.has_mail_server)

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @users("employee")
    def test_template_schedule_email(self):
        """Test scheduling email sending from template."""
        now = datetime.datetime(2024, 4, 29, 10, 49, 59)
        test_template = self.test_template.with_env(self.env)

        # schedule the mail in 3 days -> patch safe_eval.datetime access
        safe_eval_orig = safe_eval.safe_eval

        def _safe_eval_hacked(*args, **kwargs):
            """safe_eval wraps 'datetime' and freeze_time does not mock it;
            simplest solution found so far is to directly hack safe_eval just
            for this test"""
            if args[0] == "datetime.datetime.now() + datetime.timedelta(days=3)":
                return now + datetime.timedelta(days=3)
            return safe_eval_orig(*args, **kwargs)

        # patch datetime and safe_eval.datetime, as otherwise using standard 'now'
        # might lead to errors due to test running right before minute switch it
        # sometimes ends at minute+1 and assert fails - see runbot-54946
        with patch.object(
            safe_eval, "safe_eval", autospec=True, side_effect=_safe_eval_hacked
        ):
            test_template.scheduled_date = (
                "{{datetime.datetime.now() + datetime.timedelta(days=3)}}"
            )
            with freeze_time(now):
                mail_id = test_template.send_mail(self.test_record.id)
            mail = self.env["mail.mail"].sudo().browse(mail_id)
        self.assertEqual(
            mail.scheduled_date.replace(second=0, microsecond=0),
            (now + datetime.timedelta(days=3)).replace(second=0, microsecond=0),
        )
        self.assertEqual(mail.state, "outgoing")

        # check a wrong format
        test_template.scheduled_date = '{{"test " * 5}}'
        with freeze_time(now):
            mail_id = test_template.send_mail(self.test_record.id)
        mail = self.env["mail.mail"].sudo().browse(mail_id)
        self.assertFalse(mail.scheduled_date)
        self.assertEqual(mail.state, "outgoing")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_template_send_mail_body(self):
        """Test that the body and body_html is set correctly in 'mail.mail'
        when sending an email from mail.template"""
        mail_id = self.test_template.send_mail(self.test_record.id)
        mail = self.env["mail.mail"].sudo().browse(mail_id)
        body_result = "<p>EnglishBody for %s</p>" % self.test_record.name

        self.assertEqual(mail.body_html, body_result)
        self.assertEqual(mail.body, body_result)


@tagged(
    "mail_template", "multi_lang", "mail_performance", "post_install", "-at_install"
)
class TestMailTemplateLanguages(TestMailTemplateCommon):
    @classmethod
    def setUpClass(cls):
        """Create lang-based records and templates, to test batch and performances
        with language involved."""
        super().setUpClass()

        # use test notification layout
        cls.test_template.write(
            {
                "email_layout_xmlid": "mail.test_layout",
            }
        )

        # double record, one in each lang
        cls.test_records = cls.test_record + cls.env["mail.test.lang"].create(
            {
                "email_from": "ignasse.es@example.com",
                "lang": "es_ES",
                "name": "Test Record 2",
            }
        )

        # pure batch, 100 records
        cls.test_records_batch, test_partners = cls._create_records_for_batch(
            "mail.test.lang",
            100,
        )
        test_partners[:50].lang = "es_ES"

        # have a template with dynamic templates to check impact
        cls.test_template_wreports = cls.test_template.copy(
            {
                "email_layout_xmlid": "mail.test_layout",
            }
        )
        cls.test_reports = cls.env["ir.actions.report"].create(
            [
                {
                    "name": f"Test Report on {cls.test_record._name}",
                    "model": cls.test_record._name,
                    "print_report_name": "f'TestReport for {object.name}'",
                    "report_type": "qweb-pdf",
                    "report_name": "test_mail.mail_test_ticket_test_template",
                },
                {
                    "name": f"Test Report 2 on {cls.test_record._name}",
                    "model": cls.test_record._name,
                    "print_report_name": "f'TestReport2 for {object.name}'",
                    "report_type": "qweb-pdf",
                    "report_name": "test_mail.mail_test_ticket_test_template_2",
                },
            ]
        )
        cls.test_template_wreports.report_template_ids = cls.test_reports

        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # warm up group access cache: 5 queries + 1 query per user
        self.user_employee.has_group("base.group_user")
        # we don't use mock_mail_gateway thus want to mock smtp to test the stack
        self._mock_smtplib_connection()

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @warmup
    def test_template_send_email(self):
        """Test 'send_email' on template on a given record, used notably as
        contextual action."""
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(13):
            mail_id = self.test_template.with_env(self.env).send_mail(
                self.test_record.id
            )
            mail = self.env["mail.mail"].sudo().browse(mail_id)

        self.assertEqual(
            sorted(mail.attachment_ids.mapped("name")), ["first.txt", "second.txt"]
        )
        self.assertEqual(
            mail.body_html,
            f"<body><p>EnglishBody for {self.test_record.name}</p> English Layout for Lang Chatter Model</body>",
        )
        self.assertEqual(mail.email_cc, self.test_template.email_cc)
        self.assertEqual(mail.email_to, self.test_template.email_to)
        self.assertEqual(
            mail.recipient_ids, self.partner_2 | self.user_admin.partner_id
        )
        self.assertEqual(mail.subject, f"EnglishSubject for {self.test_record.name}")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @warmup
    def test_template_send_email_nolayout(self):
        """Test without layout, just to check impact"""
        self.test_template.email_layout_xmlid = False
        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(12):
            mail_id = self.test_template.with_env(self.env).send_mail(
                self.test_record.id
            )
            mail = self.env["mail.mail"].sudo().browse(mail_id)

        self.assertEqual(
            sorted(mail.attachment_ids.mapped("name")), ["first.txt", "second.txt"]
        )
        self.assertEqual(
            mail.body_html, f"<p>EnglishBody for {self.test_record.name}</p>"
        )
        self.assertEqual(mail.email_cc, self.test_template.email_cc)
        self.assertEqual(mail.email_to, self.test_template.email_to)
        self.assertEqual(
            mail.recipient_ids, self.partner_2 | self.user_admin.partner_id
        )
        self.assertEqual(mail.subject, f"EnglishSubject for {self.test_record.name}")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @warmup
    def test_template_send_email_batch(self):
        """Test 'send_email' on template in batch"""
        self.env.invalidate_all()
        # 35 (was 33, 29, itself 25). The move is six queries in, captured with
        # `query_hooks` at 83d19c2d051 (29) and diffed against the trace here:
        #   + LOCK TABLE ... IN ROW EXCLUSIVE MODE           x2
        #   + SELECT pg_get_serial_sequence(..., 'id')       x2
        #   + WITH RECURSIVE resolved ... (column types)     x2
        # The six are `odoo/db/bulk.py`'s per-table setup for the COPY create
        # path -- id sequence, row lock, column-type introspection -- one of
        # each for `mail_message` and `mail_mail`, and cached on the cursor's
        # `TransactionSchemaCache` for the rest of the transaction. They are the
        # price of writing the rows with COPY instead of INSERT, so they are the
        # same work moved rather than work added, and they do not repeat per
        # chunk: the second chunk here costs only nextval + COPY. The two
        # `INSERT INTO mail_message_res_partner_rel` left when the send stopped
        # writing message.partner_ids and are back with it: they are the
        # recipient list the chatter renders, one write per chunk.
        #
        # What this number cannot tell you is whether the send grew a per-record
        # query -- that would move it by a constant too. See
        # test_template_send_email_batch_costs_per_chunk_not_per_record below.
        with self.with_user(self.user_employee.login), self.assertQueryCount(35):
            template = self.test_template.with_env(self.env)
            mails_sudo = template.send_mail_batch(self.test_records_batch.ids)

        self.assertEqual(len(mails_sudo), 100)
        for idx, (mail, record) in enumerate(
            zip(mails_sudo, self.test_records_batch, strict=True)
        ):
            self.assertEqual(
                sorted(mail.attachment_ids.mapped("name")), ["first.txt", "second.txt"]
            )
            self.assertEqual(mail.attachment_ids.mapped("res_id"), [template.id] * 2)
            self.assertEqual(
                mail.attachment_ids.mapped("res_model"), [template._name] * 2
            )
            self.assertEqual(mail.email_cc, template.email_cc)
            self.assertEqual(mail.email_to, template.email_to)
            self.assertEqual(
                mail.recipient_ids, self.partner_2 | self.user_admin.partner_id
            )
            if idx >= 50:
                self.assertEqual(mail.subject, f"EnglishSubject for {record.name}")
            else:
                self.assertEqual(mail.subject, f"SpanishSubject for {record.name}")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_template_send_email_batch_costs_per_chunk_not_per_record(self):
        """The send issues no per-record query: its cost follows the number of
        ``mail.mail._get_send_batch_size`` chunks, and nothing else.

        This is the property the exact pin above cannot state. That pin sends
        one batch size, so a per-record query inside the send path moves it by
        a constant and reads as ordinary drift -- and the number is read for
        every unrelated change too, which is why it has spent weeks away from
        its floor while the send path was being reworked. Measured across a
        chunk boundary instead: 51 records and 100 records are two chunks
        either way, so the 49 extra records must cost nothing.

        The larger batch is measured *second* on purpose. Whatever the first
        send warms can only make the second cheaper, so the comparison is
        one-sided in the safe direction: a per-record query would put 49
        queries on the wrong side of it and no amount of warming could hide
        them. The count assertion is paired with the outcome assertion,
        because a bound alone is equally satisfied by the send not happening.
        """
        self.env.invalidate_all()
        template = self.test_template.with_env(self.env)
        record_ids = self.test_records_batch.ids
        template.send_mail_batch(record_ids[:5])  # warm the shared caches

        counts, sent = {}, {}
        for size in (51, 100):
            self.env.flush_all()
            self.env.cr.flush()
            before = self.env.cr.sql_statement_count
            mails_sudo = template.send_mail_batch(record_ids[:size])
            self.env.flush_all()
            self.env.cr.flush()
            counts[size] = self.env.cr.sql_statement_count - before
            sent[size] = len(mails_sudo)

        self.assertEqual(
            sent,
            {51: 51, 100: 100},
            "the sends have to have happened for the count to mean anything",
        )
        self.assertLessEqual(
            counts[100],
            counts[51],
            "send_mail_batch issued a query per record: 100 records cost "
            f"{counts[100]} queries against {counts[51]} for 51, and both are "
            "two chunks of at most _get_send_batch_size",
        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @warmup
    def test_template_send_email_wreport(self):
        """Test 'send_email' on template on a given record, used notably as
        contextual action, with dynamic reports involved"""
        self.env.invalidate_all()
        # tm: 22, nightly: +1
        # 21 -> 22: the budget disagreed with the annotation one line above it,
        # and the annotation was right. The extra query is this fork's own
        # `res.partner.phone` -> `phone_ids`: mail declares it `tracking=2`
        # (models/res_partner.py), and a tracked Many2many costs a
        # `res_partner_phone_number_rel` read where a stored Char cost none.
        # Chased to that query in a debug_sql trace rather than assumed --
        # it appears exactly once per pass.
        # 21 -> 22: a company's report layout is a report.config row (odoo
        # 361b8d3c6d7c); rendering the report reads it once, found and filled
        # in one query by `mixin.company.config._for_each`.
        with self.with_user(self.user_employee.login), self.assertQueryCount(22):
            mail_id = self.test_template_wreports.with_env(self.env).send_mail(
                self.test_record.id
            )
            mail = self.env["mail.mail"].sudo().browse(mail_id)

        self.assertEqual(
            sorted(mail.attachment_ids.mapped("name")),
            [
                f"TestReport for {self.test_record.name}.html",
                f"TestReport2 for {self.test_record.name}.html",
                "first.txt",
                "second.txt",
            ],
        )
        self.assertEqual(
            mail.recipient_ids, self.partner_2 | self.user_admin.partner_id
        )
        self.assertEqual(mail.subject, f"EnglishSubject for {self.test_record.name}")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @warmup
    def test_template_send_email_wreport_batch(self):
        """Test 'send_email' on template in batch with dynamic reports"""
        self.env.invalidate_all()
        # 240 (was 236, itself was 232): the same six-in / two-out move as
        # test_template_send_email_batch, on top of the dynamic-report path.
        # Measured, not inferred -- the trace here carries the same six COPY
        # setup queries and the baseline carried none.
        # 149 -> 150 for the same one query as test_template_send_email_wreport
        # above: the tracked `phone_ids` relation read. Same delta, same cause.
        # 51 -> 52: the report.config read, as above.
        with self.with_user(self.user_employee.login), self.assertQueryCount(52):
            template = self.test_template_wreports.with_env(self.env)
            mails_sudo = template.send_mail_batch(self.test_records_batch.ids)

        self.assertEqual(len(mails_sudo), 100)
        for idx, (mail, record) in enumerate(
            zip(mails_sudo, self.test_records_batch, strict=True)
        ):
            self.assertEqual(
                sorted(mail.attachment_ids.mapped("name")),
                [
                    f"TestReport for {record.name}.html",
                    f"TestReport2 for {record.name}.html",
                    "first.txt",
                    "second.txt",
                ],
            )
            self.assertEqual(
                sorted(mail.attachment_ids.mapped("res_id")),
                sorted(
                    [self.test_template_wreports.id] * 2 + [mail.mail_message_id.id] * 2
                ),
                "Attachments: attachment_ids -> linked to template, attachments -> to mail.message",
            )
            self.assertEqual(
                sorted(mail.attachment_ids.mapped("res_model")),
                sorted([template._name] * 2 + ["mail.message"] * 2),
                "Attachments: attachment_ids -> linked to template, attachments -> to mail.message",
            )
            self.assertEqual(mail.email_cc, self.test_template.email_cc)
            self.assertEqual(mail.email_to, self.test_template.email_to)
            self.assertEqual(
                mail.recipient_ids, self.partner_2 | self.user_admin.partner_id
            )
            if idx >= 50:
                self.assertEqual(mail.subject, f"EnglishSubject for {record.name}")
                self.assertEqual(
                    mail.body_html,
                    f"<body><p>EnglishBody for {record.name}</p> English Layout for Lang Chatter Model</body>",
                )
            else:
                self.assertEqual(mail.subject, f"SpanishSubject for {record.name}")
                self.assertEqual(
                    mail.body_html,
                    f"<body><p>SpanishBody for {record.name}</p> Spanish Layout para Spanish Model Description</body>",
                )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_template_send_email_wreport_batch_scalability(self):
        """Test 'send_email' on template in batch, using configuration parameter
        for batch rendering."""
        for batch_size, exp_mail_create_count in [
            (False, 2),  # unset, default is 50
            (0, 2),  # 0: fallbacks on default
            (30, 4),  # 100 / 30 -> 4 iterations
        ]:
            with self.subTest(batch_size=batch_size):
                self.env["ir.config_parameter"].sudo().set_param(
                    "mail.batch_size", batch_size
                )
                with self.with_user(self.user_employee.login), self.mock_mail_gateway():
                    template = self.test_template_wreports.with_env(self.env)
                    mails_sudo = template.send_mail_batch(self.test_records_batch.ids)

                self.assertEqual(
                    self.mail_mail_create_mocked.call_count, exp_mail_create_count
                )
                self.assertEqual(len(mails_sudo), 100)
                for idx, (mail, record) in enumerate(
                    zip(mails_sudo, self.test_records_batch, strict=True)
                ):
                    self.assertEqual(
                        sorted(mail.attachment_ids.mapped("name")),
                        [
                            f"TestReport for {record.name}.html",
                            f"TestReport2 for {record.name}.html",
                            "first.txt",
                            "second.txt",
                        ],
                    )
                    self.assertEqual(
                        sorted(mail.attachment_ids.mapped("res_id")),
                        sorted(
                            [self.test_template_wreports.id] * 2
                            + [mail.mail_message_id.id] * 2
                        ),
                        "Attachments: attachment_ids -> linked to template, attachments -> to mail.message",
                    )
                    self.assertEqual(
                        sorted(mail.attachment_ids.mapped("res_model")),
                        sorted([template._name] * 2 + ["mail.message"] * 2),
                        "Attachments: attachment_ids -> linked to template, attachments -> to mail.message",
                    )
                    self.assertEqual(mail.email_cc, self.test_template.email_cc)
                    self.assertEqual(mail.email_to, self.test_template.email_to)
                    self.assertEqual(
                        mail.recipient_ids, self.partner_2 | self.user_admin.partner_id
                    )
                    if idx >= 50:
                        self.assertEqual(
                            mail.subject, f"EnglishSubject for {record.name}"
                        )
                    else:
                        self.assertEqual(
                            mail.subject, f"SpanishSubject for {record.name}"
                        )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_template_translation_lang(self):
        """Test template rendering using lang defined directly on the record"""
        test_record = self.test_record.with_env(self.env)
        test_record.write(
            {
                "lang": "es_ES",
            }
        )
        test_template = self.test_template.with_env(self.env)

        mail_id = test_template.send_mail(test_record.id)
        mail = self.env["mail.mail"].sudo().browse(mail_id)
        self.assertEqual(
            mail.body_html,
            f"<body><p>SpanishBody for {self.test_record.name}</p> Spanish Layout para Spanish Model Description</body>",
        )
        self.assertEqual(mail.subject, f"SpanishSubject for {self.test_record.name}")

    @mute_logger("odoo.addons.mail.models.mail_mail")
    @warmup
    def test_template_translation_partner_lang(self):
        """Test template rendering using lang defined on a sub-record aka
        'partner_id.lang'"""
        test_records = self.env["mail.test.lang"].browse(self.test_records.ids)
        customers = self.env["res.partner"].create(
            [
                {
                    "email": "roberto.carlos@test.example.com",
                    "lang": "es_ES",
                    "name": "Roberto Carlos",
                },
                {
                    "email": "rob.charly@test.example.com",
                    "lang": "en_US",
                    "name": "Rob Charly",
                },
            ]
        )
        test_records[0].write({"customer_id": customers[0].id})
        test_records[1].write({"customer_id": customers[1].id})

        self.env.invalidate_all()
        with self.with_user(self.user_employee.login), self.assertQueryCount(18):
            template = self.test_template.with_env(self.env)
            mails_sudo = template.send_mail_batch(
                self.test_records.ids, email_layout_xmlid="mail.test_layout"
            )

        self.assertEqual(
            mails_sudo[0].body_html,
            f"<body><p>SpanishBody for {test_records[0].name}</p> Spanish Layout para Spanish Model Description</body>",
        )
        self.assertEqual(
            mails_sudo[0].subject, f"SpanishSubject for {test_records[0].name}"
        )
        self.assertEqual(
            mails_sudo[1].body_html,
            f"<body><p>EnglishBody for {test_records[1].name}</p> English Layout for Lang Chatter Model</body>",
        )
        self.assertEqual(
            mails_sudo[1].subject, f"EnglishSubject for {test_records[1].name}"
        )


@tagged("mail_template")
class TestMailTemplateSaveGate(MailCommon):
    """Saving a template judges the template, not the first row of its table."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model = "mail.test.ticket"
        cls.model_id = cls.env["ir.model"]._get_id(cls.model)

    def _create_template(self, **values):
        return self.env["mail.template"].create(
            {"name": "Gate", "model_id": self.model_id, **values}
        )

    def test_a_record_shaped_failure_does_not_refuse_the_save(self):
        customer = self.env["res.partner"].create({"name": "Customer"})
        bare, full = self.env[self.model].create(
            [{"name": "Bare"}, {"name": "Full", "customer_id": customer.id}]
        )
        self.assertEqual(self.env[self.model].search([], limit=1), bare)
        with self.assertLogs("odoo.addons.mail.models.mail_template", "INFO") as logs:
            template = self._create_template(
                subject="{{ object.customer_id.name.upper() }}"
            )
        self.assertIn("does not render on sample", logs.output[0])
        mail = self.env["mail.mail"].browse(template.send_mail(full.id))
        self.assertEqual(mail.subject, "CUSTOMER")

    def test_a_compile_failure_is_refused(self):
        with self.assertRaises(ValidationError):
            self._create_template(subject="{{ object.name ( }}")

    def test_a_qweb_structure_error_is_refused_not_a_traceback(self):
        with self.assertRaises(ValidationError):
            self._create_template(
                body_html=Markup('<t t-foreach="object.message_ids">x</t>')
            )

    def test_an_unknown_attribute_is_refused_without_a_row(self):
        self.assertFalse(self.env[self.model].search_count([]))
        with self.assertRaises(ValidationError):
            self._create_template(subject="{{ object.no_such_field }}")
        with self.assertRaises(ValidationError):
            self._create_template(
                body_html=Markup('<p t-out="object.customer_id.no_such_field"/>')
            )
        with self.assertRaises(ValidationError):
            self._create_template(email_to="{{ object.no_such_method() }}")
        self.assertTrue(
            self._create_template(
                body_html=Markup(
                    '<t t-foreach="object.message_ids" t-as="line">'
                    '<t t-out="line.no_such_field"/></t>'
                ),
                subject="{{ object.customer_id.name.upper() }}",
                email_to="{{ object.sudo().no_such_field }}",
            ),
            "only a chain the model graph can answer for is judged",
        )

    def test_the_verdict_does_not_depend_on_the_table_having_rows(self):
        self.assertFalse(self.env[self.model].search_count([]))
        self.assertTrue(
            self._create_template(subject="{{ object.customer_id.name.upper() }}")
        )
        with self.assertRaises(ValidationError):
            self._create_template(subject="{{ object.name ( }}")
        with self.assertRaises(ValidationError):
            self._create_template(
                body_html=Markup('<t t-foreach="object.message_ids">x</t>')
            )

    @mute_logger("odoo.addons.mail.models.mail_mail")
    def test_a_future_schedule_survives_force_send(self):
        template = self._create_template(
            body_html=Markup("<p>Later</p>"),
            email_to="later@test.example.com",
            scheduled_date="2099-01-01 10:00:00",
            subject="Later",
            use_default_to=False,
        )
        record = self.env[self.model].create({"name": "Later"})
        with self.mock_mail_gateway():
            mail = self.env["mail.mail"].browse(
                template.send_mail(record.id, force_send=True)
            )
            self.assertEqual(mail.scheduled_date, datetime.datetime(2099, 1, 1, 10))
            self.assertEqual(mail.state, "outgoing")
            mail.send()
            self.assertEqual(
                mail.state, "outgoing", "send() applies the queue's due filter"
            )
        self.assertFalse(self._mails)
        with freeze_time("2099-01-01 10:00:01"), self.mock_mail_gateway():
            mail.send()
        self.assertEqual(mail.state, "sent")
        self.assertEqual(len(self._mails), 1)


@tagged("mail_template")
class TestMailTemplateFieldLists(MailCommon):
    """The hand-maintained field lists agree on what a template renders."""

    def test_the_lists_hold_their_invariants(self):
        template_fields = self.env["mail.template"]._fields
        rendered_types = {
            fname
            for fname, field in template_fields.items()
            if field.type in ("char", "text", "html") and field.store
        }
        self.assertTrue(rendered_types >= DYNAMIC_FIELD_NAMES)
        self.assertEqual(
            self.env["mail.template"]._get_dynamic_field_names(), DYNAMIC_FIELD_NAMES
        )
        self.assertTrue(RECIPIENT_FIELD_NAMES <= DYNAMIC_FIELD_NAMES)
        self.assertEqual(
            DYNAMIC_FIELD_NAMES & TEMPLATE_SPECIFIC_FIELD_NAMES,
            RECIPIENT_FIELD_NAMES | {"scheduled_date"},
            "a dynamic field _prepare_mail_vals does not render itself is a "
            "recipient or the schedule, each with its own helper",
        )
        self.assertTrue(ATTACHMENT_FIELD_NAMES <= TEMPLATE_SPECIFIC_FIELD_NAMES)
        self.assertTrue(DYNAMIC_FIELD_NAMES - {"lang"} <= SEND_RENDER_FIELDS)
        self.assertTrue(ATTACHMENT_FIELD_NAMES <= SEND_RENDER_FIELDS)
        self.assertTrue(
            SEND_RENDER_FIELDS <= DYNAMIC_FIELD_NAMES | TEMPLATE_SPECIFIC_FIELD_NAMES
        )
        self.assertTrue(
            (SEND_RENDER_FIELDS | {"lang"}) - {"res_id"} <= template_fields.keys(),
            "res_id is the one sent value that is a record's, not the template's",
        )

    def test_the_preview_shows_a_subset_of_what_a_send_renders(self):
        preview_fields = set(self.env["mail.template.preview"]._MAIL_TEMPLATE_FIELDS)
        self.assertTrue(preview_fields <= SEND_RENDER_FIELDS)
        self.assertTrue(
            preview_fields - {"partner_to"}
            <= self.env["mail.template.preview"]._fields.keys()
        )

    def test_the_composer_maps_name_fields_of_both_models(self):
        template_fields = self.env["mail.template"]._fields
        composer_fields = self.env["mail.compose.message"]._fields
        counterparts = self.env["mixin.mail.composer"]._template_field_counterparts
        self.assertTrue(
            set(COMPOSER_FIELD_TO_TEMPLATE_FIELD.values()) <= template_fields.keys()
        )
        self.assertTrue(
            COMPOSER_FIELD_TO_TEMPLATE_FIELD.keys() - {"attachments"}
            <= composer_fields.keys(),
            "every key is a composer field, except the attachments render key",
        )
        self.assertTrue(
            counterparts.items() <= COMPOSER_FIELD_TO_TEMPLATE_FIELD.items()
        )
        self.assertEqual(
            TEMPLATE_FIELD_TO_COMPOSER_FIELD,
            {template: composer for composer, template in counterparts.items()},
        )
        self.assertTrue(counterparts.keys() <= composer_fields.keys())
        self.assertTrue(set(counterparts.values()) <= template_fields.keys())
        self.assertTrue(
            TEMPLATE_RENDER_FIELDS
            <= (DYNAMIC_FIELD_NAMES | ATTACHMENT_FIELD_NAMES) - RECIPIENT_FIELD_NAMES
        )
