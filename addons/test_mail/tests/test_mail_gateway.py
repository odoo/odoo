import base64
import email
import email.policy
import itertools
import socket
from datetime import datetime, timedelta
from unittest.mock import DEFAULT, patch

from markupsafe import Markup

from odoo import Command, exceptions
from odoo.db import Cursor
from odoo.tests import Form, RecordCapturer, tagged
from odoo.tools import mute_logger
from odoo.tools.mail import email_normalize, email_split_and_format, formataddr

from odoo.addons.mail.models.mail_message import MailMessage
from odoo.addons.mail.models.mixin_mail_gateway import (
    MixinMailGateway,
    Route,
    RouteVerdict,
)
from odoo.addons.mail.tests.common import MailCommon, mail_new_test_user
from odoo.addons.test_mail.data import test_mail_data
from odoo.addons.test_mail.data.test_mail_data import (
    MAIL_TEMPLATE,
    MAIL_TEMPLATE_EXTRA_HTML,
    THAI_EMAIL_WINDOWS_874,
)
from odoo.addons.test_mail.models.mail_test_ticket import MailTestTicket
from odoo.addons.test_mail.models.test_mail_models import (
    MailTestGateway,
    MailTestGatewayGroups,
)


@tagged("mail_gateway")
class TestEmailParsing(MailCommon):
    def test_message_parse_and_replace_binary_octetstream(self):
        """Incoming email containing a wrong Content-Type as described in RFC2046/section-3"""
        received_mail = self.from_string(
            test_mail_data.MAIL_MULTIPART_BINARY_OCTET_STREAM
        )
        with self.assertLogs("odoo.addons.mail.tools.mime", level="WARNING") as capture:
            extracted_mail = self.env[
                "mixin.mail.thread"
            ]._message_parse_extract_payload(received_mail, {})

        self.assertEqual(len(extracted_mail["attachments"]), 1)
        attachment = extracted_mail["attachments"][0]
        self.assertEqual(attachment.fname, "hello_world.dat")
        self.assertEqual(attachment.content, b"Hello world\n")
        self.assertEqual(
            capture.output,
            [
                (
                    "WARNING:odoo.addons.mail.tools.mime:Message containing an unexpected "
                    "Content-Type 'binary/octet-stream', assuming 'application/octet-stream'"
                ),
            ],
        )

    def test_message_parse_and_replace_wildcard(self):
        """Incoming email containing a wrong Content-Type (*/*) as described in RFC2046/section-3"""
        mail_with_wildcard_mime = self.format(
            test_mail_data.MAIL_PDF_MIME_TEMPLATE, pdf_mime="*/*"
        )
        self.assertIn(
            "Content-Type: */*",
            mail_with_wildcard_mime,
            "Wildcard for content-type not found",
        )
        with self.assertLogs("odoo.addons.mail.tools.mime", level="WARNING") as capture:
            extracted_mail = self.env["mixin.mail.thread"].message_parse(
                self.from_string(mail_with_wildcard_mime)
            )

        self.assertEqual(len(extracted_mail["attachments"]), 1)
        attachment = extracted_mail["attachments"][0]
        self.assertEqual(attachment.fname, "scan_soraya.lernout_1691652648.pdf")
        self.assertEqual(
            capture.output,
            [
                (
                    "WARNING:odoo.addons.mail.tools.mime:Message containing an unexpected "
                    "Content-Type '*/*', assuming 'application/octet-stream'"
                ),
            ],
        )

    def test_message_parse_body(self):
        # test pure plaintext
        plaintext = self.format(
            test_mail_data.MAIL_TEMPLATE_PLAINTEXT,
            email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
        )
        res = self.env["mixin.mail.thread"].message_parse(self.from_string(plaintext))
        self.assertIn("Please call me as soon as possible this afternoon!", res["body"])

        # test pure html
        html = self.format(
            test_mail_data.MAIL_TEMPLATE_HTML,
            email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
        )
        res = self.env["mixin.mail.thread"].message_parse(self.from_string(html))
        self.assertIn(
            "<p>Please call me as soon as possible this afternoon!</p>", res["body"]
        )
        self.assertNotIn("<!DOCTYPE", res["body"])

        # test multipart / text and html -> html has priority
        multipart = self.format(
            MAIL_TEMPLATE,
            email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
        )
        res = self.env["mixin.mail.thread"].message_parse(self.from_string(multipart))
        self.assertIn(
            "<p>Please call me as soon as possible this afternoon!</p>", res["body"]
        )

        # test multipart / mixed
        res = self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_MULTIPART_MIXED)
        )
        self.assertNotIn(
            "Should create a multipart/mixed: from gmail, *bold*, with attachment",
            res["body"],
            "message_parse: text version should not be in body after parsing multipart/mixed",
        )
        self.assertIn(
            '<div dir="ltr">Should create a multipart/mixed: from gmail, <b>bold</b>, with attachment.<br clear="all"><div><br></div>',
            res["body"],
            "message_parse: html version should be in body after parsing multipart/mixed",
        )

        res = self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_MULTIPART_MIXED_TWO)
        )
        self.assertNotIn(
            "First and second part",
            res["body"],
            "message_parse: text version should not be in body after parsing multipart/mixed",
        )
        self.assertIn(
            "First part",
            res["body"],
            "message_parse: first part of the html version should be in body after parsing multipart/mixed",
        )
        self.assertIn(
            "Second part",
            res["body"],
            "message_parse: second part of the html version should be in body after parsing multipart/mixed",
        )

        res = self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_SINGLE_BINARY)
        )
        self.assertEqual(res["body"], "")
        self.assertEqual(res["attachments"][0][0], "thetruth.pdf")

        res = self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_FORWARDED)
        )
        self.assertIn(
            res["recipients"],
            [
                "lucie@petitebedaine.fr,raoul@grosbedon.fr",
                "raoul@grosbedon.fr,lucie@petitebedaine.fr",
            ],
        )

        res = self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_MULTIPART_WEIRD_FILENAME)
        )
        self.assertEqual(res["attachments"][0][0], "62_@;,][)=.(ÇÀÉ.txt")

    def test_message_parse_attachment_pdf_nonstandard_mime(self):
        # This test checks if aliasing content-type (mime type) of "pdf" with "application/pdf" works correctly. (i.e. Treat "pdf" as "application/pdf")

        # Baseline check. Parsing mail with "application/pdf"
        mail_with_standard_mime = self.format(
            test_mail_data.MAIL_PDF_MIME_TEMPLATE, pdf_mime="application/pdf"
        )
        res_std = self.env["mixin.mail.thread"].message_parse(
            self.from_string(mail_with_standard_mime)
        )
        self.assertEqual(
            res_std["attachments"][0].content,
            test_mail_data.PDF_PARSED,
            "Attachment with Content-Type: application/pdf must parse without error",
        )

        # Parsing the same email, but with content-type set to "pdf"
        mail_with_aliased_mime = self.format(
            test_mail_data.MAIL_PDF_MIME_TEMPLATE, pdf_mime="pdf"
        )
        res_alias = self.env["mixin.mail.thread"].message_parse(
            self.from_string(mail_with_aliased_mime)
        )
        self.assertEqual(
            res_alias["attachments"][0].content,
            test_mail_data.PDF_PARSED,
            "Attachment with aliased Content-Type: pdf must parse without error",
        )

    def test_message_parse_bugs(self):
        """Various corner cases or message parsing"""
        # message without Final-Recipient
        self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_NO_FINAL_RECIPIENT)
        )

        # message with empty body (including only void characters)
        res = self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_NO_BODY)
        )
        self.assertEqual(
            res["body"], "\n \n", "Gateway should not crash with void content"
        )

    def test_message_parse_eml(self):
        # Test that the parsing of mail with embedded emails as eml(msg) which generates empty attachments, can be processed.
        mail = self.format(
            test_mail_data.MAIL_EML_ATTACHMENT,
            email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
            to=f"generic@{self.alias_domain}",
            msg_id="<cb7eaf62-58dc-2017-148c-305d0c78892f@odoo.com>",
            references="<f3b9f8f8-28fa-2543-cab2-7aa68f679ebb@odoo.com>",
            subject="Re: test attac",
        )
        self.env["mixin.mail.thread"].message_parse(self.from_string(mail))

    def test_message_parse_eml_bounce_headers(self):
        # Test Text/RFC822-Headers MIME content-type
        msg_id = "<861878175823148.1577183525.736005783081055-odoo-19177-account.invoice@mycompany.example.com>"
        mail = self.format(
            test_mail_data.MAIL_EML_ATTACHMENT_BOUNCE_HEADERS,
            email_from="MAILER-DAEMON@example.com (Mail Delivery System)",
            to="test_bounce+82240-account.invoice-19177@mycompany.example.com",
            # msg_id goes to the attachment's Message-Id header
            msg_id=msg_id,
        )
        res = self.env["mixin.mail.thread"].message_parse(self.from_string(mail))

        self.assertEqual(
            res["bounced_msg_ids"],
            [msg_id],
            "Message-Id is not extracted from Text/RFC822-Headers attachment",
        )

    def test_message_parse_extract_bounce_rfc822_headers_qp(self):
        # Incoming bounce for unexisting Outlook address
        # bounce back sometimes with a Content-Type `text/rfc822-headers`
        # and Content-Type-Encoding `quoted-printable`
        partner = self.env["res.partner"].create(
            {"name": "Mitchelle Admine", "email": "rdesfrdgtfdrfesd@outlook.com"}
        )
        message = self.env["mail.message"].create(
            {
                "message_id": "<368396033905967.1673346177.695352554321289-odoo-11-sale.order@eupp00>"
            }
        )
        incoming_bounce = self.format(
            test_mail_data.MAIL_BOUNCE_QP_RFC822_HEADERS,
            email_from="MAILER-DAEMON@mailserver.odoo.com (Mail Delivery System)",
            email_to="bounce@xxx.odoo.com",
            delivered_to="bounce@xxx.odoo.com",
        )
        msg = self.env["mixin.mail.thread"].message_parse(
            self.from_string(incoming_bounce)
        )
        self.assertEqual(
            msg["bounced_email"],
            partner.email,
            "The sender email should be correctly parsed",
        )
        self.assertEqual(
            msg["bounced_partner"], partner, "A partner with this email should exist"
        )
        self.assertEqual(
            msg["bounced_msg_ids"][0],
            message.message_id,
            "The sender message-id should correctly parsed",
        )
        self.assertEqual(
            msg["bounced_message"],
            message,
            "An existing message with this message_id should exist",
        )

    def test_message_parse_plaintext(self):
        """Incoming email in plaintext should be stored as html"""
        mail = self.format(
            test_mail_data.MAIL_TEMPLATE_PLAINTEXT,
            email_from='"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>',
            to=f"generic@{self.alias_domain}",
        )
        res = self.env["mixin.mail.thread"].message_parse(self.from_string(mail))
        self.assertIn(
            "<pre>\nPlease call me as soon as possible this afternoon!\n\n--\nSylvie\n</pre>",
            res["body"],
        )

    def test_message_parse_xhtml(self):
        # Test that the parsing of XHTML mails does not fail
        self.env["mixin.mail.thread"].message_parse(
            self.from_string(test_mail_data.MAIL_XHTML)
        )


@tagged("mail_gateway")
class MailGatewayCommon(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mail_test_gateway_model = cls.env["ir.model"]._get("mail.test.gateway")
        cls.mail_test_gateway_company_model = cls.env["ir.model"]._get(
            "mail.test.gateway.company"
        )
        cls.email_from = '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>'

        cls.test_record = (
            cls.env["mail.test.gateway"]
            .with_context(mail_create_nolog=True)
            .create(
                {
                    "name": "Test",
                    "email_from": "ignasse@example.com",
                }
            )
        )

        cls.partner_1 = cls.env["res.partner"].create(
            {
                "name": "Valid Lelitre",
                "email": "valid.lelitre@agrolait.com",
            }
        )
        # groups@test.mycompany.com will cause the creation of new mail.test.gateway
        cls.alias = cls.env["mail.alias"].create(
            {
                "alias_domain_id": cls.mail_alias_domain.id,
                "alias_contact": "everyone",
                "alias_model_id": cls.mail_test_gateway_model.id,
                "alias_name": "groups",
            }
        )
        # groups@test.mycompany2.com will cause the creation of new mail.test.gateway.company
        cls.alias_c2 = cls.env["mail.alias"].create(
            {
                "alias_defaults": {
                    "company_id": cls.company_2.id,
                },
                "alias_domain_id": cls.mail_alias_domain_c2.id,
                "alias_contact": "everyone",
                "alias_model_id": cls.mail_test_gateway_company_model.id,
                "alias_name": "groups",
            }
        )

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls._create_gateway_message(
            cls.test_record,
            "123456",
            date=datetime(2025, 11, 19, 10, 30, 0),
        )

    def _reinject(self, force_msg_id=False, debug_log=False):
        """Tool to automatically 'inject' an outgoing mail into the gateway.
        Content changes.

        :param str force_msg_id: allow to change the msg_id to simulate stupid
            email providers that change message IDs;
        """
        self.assertEqual(len(self._mails), 1)
        mail = self._mails[0]
        extra = f"References: {mail['references']}"
        with self.mock_mail_gateway(), self.mock_mail_app():
            self.format_and_process(
                MAIL_TEMPLATE,
                mail["email_from"],
                ",".join(mail["email_to"]),
                msg_id=force_msg_id or mail["message_id"],
                extra=extra,
                debug_log=debug_log,
            )

    @classmethod
    def _create_gateway_message(cls, record, msg_id_prefix, **values):
        msg_values = {
            "author_id": cls.partner_1.id,
            "date": cls.env.cr.now(),
            "email_from": cls.partner_1.email_formatted,
            "body": "<p>Generic body</p>",
            "message_id": f"<{msg_id_prefix}-odoo-{record.id}-{record._name}@{socket.gethostname()}>",
            "message_type": "email",
            "model": record._name,
            "res_id": record.id,
            "subject": "Generic Message",
            "subtype_id": cls.env.ref("mail.mt_comment").id,
        }
        msg_values.update(**values)
        return cls.env["mail.message"].create(msg_values)


@tagged("mail_gateway")
class TestMailgateway(MailGatewayCommon):
    def test_assert_initial_values(self):
        """Just some basics checks to ensure tests coherency"""
        self.assertEqual(len(self.test_record.message_ids), 1)

    # --------------------------------------------------
    # Base low-level tests
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_alias_basic(self):
        """Test details of created message going through mailgateway"""
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Specific",
        )

        # Test: one group created by mailgateway administrator as user_id is not set
        self.assertEqual(
            len(record), 1, "message_process: a new mail.test should have been created"
        )
        res = record.get_metadata()[0].get("create_uid") or [None]
        self.assertEqual(res[0], self.env.uid)

        # Test: one message that is the incoming email
        self.assertEqual(len(record.message_ids), 1)
        msg = record.message_ids[0]
        self.assertEqual(msg.subject, "Specific")
        self.assertIn("Please call me as soon as possible this afternoon!", msg.body)
        self.assertEqual(msg.message_type, "email")
        self.assertEqual(msg.subtype_id, self.env.ref("mail.mt_comment"))

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_cid(self):
        origin_message_parse_extract_payload = (
            MixinMailGateway._message_parse_extract_payload
        )

        def _message_parse_extract_payload(this, *args, **kwargs):
            res = origin_message_parse_extract_payload(this, *args, **kwargs)
            self.assertTrue(
                isinstance(res["body"], str),
                "Body from extracted payload should still be a string.",
            )
            return res

        with patch.object(
            MixinMailGateway,
            "_message_parse_extract_payload",
            _message_parse_extract_payload,
        ):
            record = self.format_and_process(
                test_mail_data.MAIL_MULTIPART_IMAGE,
                self.email_from,
                f"groups@{self.alias_domain}",
            )
        message = record.message_ids[0]
        for attachment in message.attachment_ids:
            self.assertIn(f"/web/image/{attachment.id}", message.body)
        self.assertEqual(
            set(message.attachment_ids.mapped("name")),
            {"rosaçée.gif", "verte!µ.gif", "orangée.gif"},
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_followers(self):
        """Incoming email: recognized author not archived and not odoobot:
        added as follower. Also test corner cases: archived."""
        partner_archived = self.env["res.partner"].create(
            {
                "active": False,
                "email": "archived.customer@text.example.com",
                "phone_ids": [
                    Command.create({"number": "0032455112233", "type": "landline"})
                ],
                "name": "Archived Customer",
                "type": "contact",
            }
        )

        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"groups@{self.alias_domain}",
            )

        self.assertEqual(
            record.message_ids[0].author_id,
            self.partner_1,
            "message_process: recognized email -> author_id",
        )
        self.assertEqual(
            record.message_ids[0].email_from, self.partner_1.email_formatted
        )
        self.assertFalse(
            record.message_partner_ids,
            "message_process: recognized email -> but not added as follower as external",
        )

        # just an email -> no follower
        with self.mock_mail_gateway():
            record2 = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Another Email",
            )

        self.assertEqual(record2.message_ids[0].author_id, self.env["res.partner"])
        self.assertEqual(record2.message_ids[0].email_from, self.email_from)
        self.assertEqual(
            record2.message_follower_ids.partner_id,
            self.env["res.partner"],
            "message_process: unrecognized email -> no follower",
        )
        self.assertEqual(
            record2.message_partner_ids,
            self.env["res.partner"],
            "message_process: unrecognized email -> no follower",
        )

        # archived partner -> no follower
        with self.mock_mail_gateway():
            record3 = self.format_and_process(
                MAIL_TEMPLATE,
                partner_archived.email_formatted,
                f"groups@{self.alias_domain}",
                subject="Archived Partner",
            )

        self.assertEqual(record3.message_ids[0].author_id, self.env["res.partner"])
        self.assertEqual(
            record3.message_ids[0].email_from, partner_archived.email_formatted
        )
        self.assertEqual(
            record3.message_follower_ids.partner_id,
            self.env["res.partner"],
            "message_process: archived partner -> no follower",
        )
        self.assertEqual(
            record3.message_partner_ids,
            self.env["res.partner"],
            "message_process: archived partner -> no follower",
        )

        # partner_root -> never again
        odoobot = self.env.ref("base.partner_root")
        odoobot.active = True
        odoobot.email = "odoobot@example.com"
        with self.mock_mail_gateway():
            record4 = self.format_and_process(
                MAIL_TEMPLATE,
                odoobot.email_formatted,
                f"groups@{self.alias_domain}",
                subject="Odoobot Automatic Answer",
            )

        self.assertEqual(record4.message_ids[0].author_id, odoobot)
        self.assertEqual(record4.message_ids[0].email_from, odoobot.email_formatted)
        self.assertEqual(
            record4.message_follower_ids.partner_id,
            self.env["res.partner"],
            "message_process: odoobot -> no follower",
        )
        self.assertEqual(
            record4.message_partner_ids,
            self.env["res.partner"],
            "message_process: odoobot -> no follower",
        )

        # internal user -> ok
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_employee.email_formatted,
                f"groups@{self.alias_domain}",
                subject="Internal Author",
            )

        self.assertEqual(
            record.message_ids[0].author_id,
            self.partner_employee,
            "message_process: recognized email -> author_id",
        )
        self.assertEqual(
            record.message_ids[0].email_from, self.user_employee.email_formatted
        )
        self.assertEqual(
            record.message_partner_ids,
            self.partner_employee,
            "message_process: recognized email -> added as follower",
        )

    # --------------------------------------------------
    # Author recognition
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_email_email_from(self):
        """Incoming email: not recognized author: email_from, no author_id, no followers"""
        record = self.format_and_process(
            MAIL_TEMPLATE, self.email_from, f"groups@{self.alias_domain}"
        )
        self.assertFalse(
            record.message_ids[0].author_id,
            "message_process: unrecognized email -> no author_id",
        )
        self.assertEqual(record.message_ids[0].email_from, self.email_from)
        self.assertEqual(
            len(record.message_partner_ids),
            0,
            "message_process: newly create group should not have any follower",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_email_author(self):
        """Incoming email: recognized author: email_from, author_id, added as follower"""
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"groups@{self.alias_domain}",
                subject="Test1",
            )

        self.assertEqual(
            record.message_ids[0].author_id,
            self.partner_1,
            "message_process: recognized email -> author_id",
        )
        self.assertEqual(
            record.message_ids[0].email_from, self.partner_1.email_formatted
        )
        self.assertNotSentEmail()  # No notification / bounce should be sent

        # Email recognized if partner has a formatted email
        self.partner_1.write({"email": f'"Valid Lelitre" <{self.partner_1.email}>'})
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email,
            f"groups@{self.alias_domain}",
            subject="Test2",
        )

        self.assertEqual(
            record.message_ids[0].author_id,
            self.partner_1,
            "message_process: recognized email -> author_id",
        )
        self.assertEqual(record.message_ids[0].email_from, self.partner_1.email)
        self.assertNotSentEmail()  # No notification / bounce should be sent

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_email_author_multiemail(self):
        """Incoming email: recognized author: check multi/formatted email in field"""
        test_email = "valid.lelitre@agrolait.com"
        # Email not recognized if partner has a multi-email (source = formatted email)
        self.partner_1.write(
            {"email": f'{test_email}, "Valid Lelitre" <another.email@test.example.com>'}
        )
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                f'"Valid Lelitre" <{test_email}>',
                f"groups@{self.alias_domain}",
                subject="Test3",
            )

        self.assertEqual(
            record.message_ids[0].author_id,
            self.partner_1,
            "message_process: found author based on first found email normalized, even with multi emails",
        )
        self.assertEqual(
            record.message_ids[0].email_from, f'"Valid Lelitre" <{test_email}>'
        )
        self.assertNotSentEmail()  # No notification / bounce should be sent

        # Email not recognized if partner has a multi-email (source = std email)
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                test_email,
                f"groups@{self.alias_domain}",
                subject="Test4",
            )

        self.assertEqual(
            record.message_ids[0].author_id,
            self.partner_1,
            "message_process: found author based on first found email normalized, even with multi emails",
        )
        self.assertEqual(record.message_ids[0].email_from, test_email)
        self.assertNotSentEmail()  # No notification / bounce should be sent

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.tests",
    )
    def test_message_process_email_author_partner_find(self):
        """Finding the partner based on email, based on partner / user / follower"""
        self.alias.write({"alias_force_thread_id": self.test_record.id})
        from_1 = self.env["res.partner"].create(
            {"name": "Brice Denisse", "email": "from.test@example.com"}
        )

        self.format_and_process(
            MAIL_TEMPLATE, from_1.email_formatted, f"groups@{self.alias_domain}"
        )
        self.assertEqual(self.test_record.message_ids[0].author_id, from_1)
        self.test_record.message_unsubscribe([from_1.id])

        from_2 = mail_new_test_user(
            self.env,
            login="B",
            groups="base.group_user",
            name="User Denisse",
            email="from.test@example.com",
        )

        self.format_and_process(
            MAIL_TEMPLATE, from_1.email_formatted, f"groups@{self.alias_domain}"
        )
        self.assertEqual(self.test_record.message_ids[0].author_id, from_2.partner_id)
        self.test_record.message_unsubscribe([from_2.partner_id.id])

        from_3 = self.env["res.partner"].create(
            {"name": "FOllower Denisse", "email": "from.test@example.com"}
        )
        self.test_record.message_subscribe([from_3.id])

        self.format_and_process(
            MAIL_TEMPLATE, from_1.email_formatted, f"groups@{self.alias_domain}"
        )
        self.assertEqual(self.test_record.message_ids[0].author_id, from_3)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_email_author_exclude_alias(self):
        """Do not set alias as author to avoid including aliases in discussions"""
        self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "from.test",
                "alias_model_id": self.env["ir.model"]._get("mail.test.gateway").id,
            }
        )
        alias_impostors = self.env["res.partner"].create(
            [
                {
                    "name": "Alias Impostor",
                    "email": f"from.test@{self.mail_alias_domain.name}",
                },
                {
                    "name": "Alias Domain Impostor",
                    "email": self.mail_alias_domain.catchall_email,
                },
            ]
        )

        for email_from, impostor in [
            (f"from.test@{self.mail_alias_domain.name}", alias_impostors[0]),
            (
                f'"Brice Denisse" <from.test@{self.mail_alias_domain.name}>',
                alias_impostors[0],
            ),
            (
                f'"Catchall Impostor" <{self.mail_alias_domain.catchall_email}>',
                alias_impostors[1],
            ),
        ]:
            with self.subTest(email_from=email_from):
                record = self.format_and_process(
                    MAIL_TEMPLATE,
                    email_from,
                    f"groups@{self.alias_domain}",
                    subject=f"Incoming email from {email_from}",
                )
                self.assertFalse(
                    record.message_ids[0].author_id,
                    f"Should not link a partner, especially not {impostor.name}",
                )
                self.assertEqual(record.message_ids[0].email_from, email_from)

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_owner_author_notify(self):
        """Make sure users are notified when a reply is sent to an alias address.
        Alias owner should impact the message creator, but not notifications."""
        test_record = self.env["mail.test.ticket"].create({})
        author_partner = self.env["res.partner"].create(
            {
                "name": "Author",
                "email": f"author-partner@{self.alias_domain}",
            }
        )
        message = self.env[
            "mail.message"
        ].create(
            {
                "body": "<p>test</p>",
                "email_from": f"author-partner@{self.alias_domain}",  # email sent by author who also has an alias with their email
                "message_type": "email_outgoing",
                "model": test_record._name,
                "res_id": test_record.id,
            }
        )
        self.env["mail.alias"].create(
            {
                "alias_model_id": self.env["ir.model"]._get_id(test_record._name),
                "alias_name": "author-partner",
            }
        )

        test_record.message_subscribe(
            (author_partner | self.user_employee.partner_id).ids
        )

        messages = test_record.message_ids

        self.assertFalse(
            self.user_root.active, "notification logic relies on odoobot being archived"
        )

        test_users = [self.user_employee, self.user_root]
        email_tos = [
            f"author-partner@{self.alias_domain}",
            f"some_non_aliased_email@{self.alias_domain}",
        ]
        for email_to, test_user in itertools.product(email_tos, test_users):
            with self.subTest(test_user=test_user, email_to=email_to):
                with self.mock_mail_gateway(), self.mock_mail_app():
                    self.format_and_process(
                        MAIL_TEMPLATE,
                        self.email_from,
                        email_to,
                        subject=message.message_id,
                        extra=f"In-Reply-To:\r\n\t{message.message_id}\n",
                        model=None,
                        with_user=test_user,
                    )
                new_messages = test_record.message_ids - messages

                self.assertEqual(len(new_messages), 1)
                self.assertEqual(
                    new_messages.create_uid,
                    self.user_root,
                    "Odoobot should be creating the message",
                )

                # Make sure the alias owner is notified if they are a follower
                self.assertNotified(
                    new_messages,
                    [
                        {
                            "partner": self.user_employee.partner_id,
                            "is_read": False,
                            "type": "inbox",
                        }
                    ],
                )
                # never notify the author of the incoming message
                with self.assertRaises(Exception):
                    self.assertNotified(new_messages, [{"partner": author_partner}])

            messages = test_record.message_ids

    # --------------------------------------------------
    # Alias configuration
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
    )
    def test_message_process_alias_config_bounced_content(self):
        """Custom bounced message for the alias => Received this custom message"""
        self.alias.write(
            {
                "alias_contact": "partners",
                "alias_bounced_content": "<p>What Is Dead May Never Die</p>",
            }
        )

        # Test: custom bounced content
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Should Bounce",
            )
        self.assertFalse(record, "message_process: should have bounced")
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
            body_content="<p>What Is Dead May Never Die</p>",
        )

        for empty_content in [
            "<p><br></p>",
            "<p><br> </p>",
            "<p><br /></p >",
            '<p style="margin: 4px"></p>',
            '<div style="margin: 4px"></div>',
            '<p class="oe_testing"><br></p>',
            '<p><span style="font-weight: bolder;"><font style="color: rgb(255, 0, 0);" class=" "></font></span><br></p>',
        ]:
            self.alias.write(
                {
                    "alias_contact": "partners",
                    "alias_bounced_content": empty_content,
                }
            )

            # Test: with "empty" bounced content (simulate view, putting always '<p></br></p>' in html field)
            with self.mock_mail_gateway():
                record = self.format_and_process(
                    MAIL_TEMPLATE,
                    self.email_from,
                    f"groups@{self.alias_domain}",
                    subject="Should Bounce",
                )
            self.assertFalse(record, "message_process: should have bounced")
            # Check if default (hardcoded) value is in the mail content
            self.assertSentEmail(
                f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
                ["whatever-2a840@postmaster.twitter.com"],
                body_content=f"<p>Dear Sender,<br /><br />The message below could not be accepted by the address {self.alias.display_name.lower()}",
            )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.models.mail_mail",
        "odoo.models.unlink",
    )
    def test_message_process_alias_config_bounced_to(self):
        """Check bounce message contains the bouncing alias, not a generic "to" """
        self.alias.write({"alias_contact": "partners"})
        bounce_message_with_alias = f"<p>Dear Sender,<br /><br />The message below could not be accepted by the address {self.alias.display_name.lower()}"

        # Bounce is To
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                cc="other@gmail.com",
                subject="Should Bounce",
            )
        self.assertIn(bounce_message_with_alias, self._mails[0].get("body"))

        # Bounce is CC
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                "other@gmail.com",
                cc=f"groups@{self.alias_domain}",
                subject="Should Bounce",
            )
        self.assertIn(bounce_message_with_alias, self._mails[0].get("body"))

        # Bounce is part of To
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"other@gmail.com, groups@{self.alias_domain}",
                subject="Should Bounce",
            )
        self.assertIn(bounce_message_with_alias, self._mails[0].get("body"))

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.models.mail_mail",
        "odoo.models",
        "odoo.db",
    )
    def test_message_process_alias_config_invalid_defaults(self):
        """Sending a mail to a misconfigured alias must change its status to
        invalid and notify sender."""
        test_model_track = self.env["ir.model"]._get("mail.test.track")
        container_custom = self.env["mail.test.container"].create({})
        alias_valid = (
            self.env["mail.alias"]
            .with_user(self.user_admin)
            .create(
                {
                    "alias_domain_id": self.mail_alias_domain.id,
                    "alias_name": "valid",
                    "alias_model_id": test_model_track.id,
                    "alias_contact": "everyone",
                    "alias_defaults": f"{{'container_id': {container_custom.id}}}",
                }
            )
        )
        self.assertEqual(alias_valid.create_uid, self.user_admin)

        # Test that it works when the reference to container_id in alias default is not dangling.
        self.assertEqual(alias_valid.alias_status, "not_tested")
        with (
            self.mock_mail_gateway(),
            patch(
                "odoo.addons.mail.models.mixin_mail_gateway.MixinMailGateway._routing_bounce_alias",
                autospec=True,
            ) as _routing_bounce_alias_mock,
        ):
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"valid@{self.alias_domain}",
                subject="Valid",
                target_model=test_model_track.model,
            )
        _routing_bounce_alias_mock.assert_not_called()
        self.assertNotSentEmail()
        self.assertEqual(record.container_id, container_custom)
        self.assertEqual(alias_valid.alias_status, "valid")

        # Test with a dangling reference that must trigger bounce emails and set the alias status to invalid.
        container_custom.unlink()
        with (
            self.assertRaises(Exception),
            patch(
                "odoo.addons.mail.models.mixin_mail_gateway.MixinMailGateway._routing_bounce_alias",
                autospec=True,
            ) as _routing_bounce_alias_mock,
        ):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"valid@{self.alias_domain}",
                subject="Invalid",
                target_model=test_model_track.model,
            )

        # method executed in another transaction, so we cannot test its result directly but just below
        _routing_bounce_alias_mock.assert_called_once()

        # replay it on the test transaction to validate its effect. The mock is
        # autospec'd on the router's method, so `self` -- the thread mixin that sends
        # the bounce -- is the first argument and the alias is the second.
        _thread, alias, message, message_dict = (
            _routing_bounce_alias_mock.call_args.args
        )
        with self.mock_mail_gateway():
            self.env["mixin.mail.thread"]._routing_bounce_alias(
                self.env["mail.alias"].browse(alias.id),  # in the test transaction
                message,
                message_dict,
            )

        self.assertEqual(alias_valid.alias_status, "invalid")
        # Not sent to self.email_from because a return path is present in MAIL_TEMPLATE
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Invalid",
            body=alias_valid._get_alias_invalid_body(message_dict),
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_alias_defaults(self):
        """Test alias defaults and inner values"""
        self.alias.write({"alias_defaults": "{'custom_field': 'defaults_custom'}"})
        self.assertEqual(self.alias.alias_status, "not_tested")

        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Specific",
        )
        self.assertEqual(self.alias.alias_status, "valid")
        self.assertEqual(len(record), 1)
        self.assertEqual(record.name, "Specific")
        self.assertEqual(record.custom_field, "defaults_custom")

        self.alias.write({"alias_defaults": "{}"})
        self.assertEqual(
            self.alias.alias_status,
            "not_tested",
            "Updating alias_defaults must reset status",
        )

        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Specific2",
        )
        self.assertEqual(len(record), 1)
        self.assertEqual(record.name, "Specific2")
        self.assertFalse(record.custom_field)
        self.assertEqual(self.alias.alias_status, "valid")

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_alias_everyone(self):
        """Incoming email: everyone: new record + message_new"""
        self.alias.write({"alias_contact": "everyone"})

        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Specific",
        )
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
    )
    def test_message_process_alias_partners_bounce(self):
        """Incoming email from an unknown partner on a Partners only alias -> bounce + test bounce email"""
        self.alias.write({"alias_contact": "partners"})

        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Should Bounce",
            )
        self.assertFalse(record)
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Should Bounce",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
    )
    def test_message_process_alias_partners_bounce_no_subject(self):
        """A bounced mail carrying no Subject must not be answered with the
        literal subject "Re: None" -- message.get() returns None for an absent
        header, and the bounce values interpolated it straight into "Re: %s"."""
        self.alias.write({"alias_contact": "partners"})

        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="",
            )
        self.assertFalse(record)
        sent = self._find_sent_email(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
        )
        self.assertTrue(sent, "the mail should still have bounced")
        self.assertNotIn("None", sent["subject"])
        self.assertEqual(sent["subject"], "Re:")

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
    )
    def test_message_process_alias_followers_bounce(self):
        """Incoming email from unknown partner / not follower partner on a Followers only alias -> bounce"""
        self.alias.write(
            {
                "alias_contact": "followers",
                "alias_parent_model_id": self.env["ir.model"]
                ._get("mail.test.gateway")
                .id,
                "alias_parent_thread_id": self.test_record.id,
            }
        )

        # Test: unknown on followers alias -> bounce
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Should Bounce",
            )
        self.assertFalse(record, "message_process: should have bounced")
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Should Bounce",
        )

        # Test: partner on followers alias -> bounce
        self._init_mail_mock()
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"groups@{self.alias_domain}",
                subject="Should Bounce",
            )
        self.assertFalse(record, "message_process: should have bounced")
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Should Bounce",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_alias_partner(self):
        """Incoming email from a known partner on a Partners alias -> ok (+ test on alias.user_id)"""
        self.alias.write({"alias_contact": "partners"})
        record = self.format_and_process(
            MAIL_TEMPLATE, self.partner_1.email_formatted, f"groups@{self.alias_domain}"
        )

        # Test: one group created by alias user
        self.assertEqual(len(record), 1)
        self.assertEqual(len(record.message_ids), 1)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_alias_followers(self):
        """Incoming email from a parent document follower on a Followers only alias -> ok"""
        self.alias.write(
            {
                "alias_contact": "followers",
                "alias_parent_model_id": self.env["ir.model"]
                ._get("mail.test.gateway")
                .id,
                "alias_parent_thread_id": self.test_record.id,
            }
        )
        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        record = self.format_and_process(
            MAIL_TEMPLATE, self.partner_1.email_formatted, f"groups@{self.alias_domain}"
        )

        # Test: one group created by Raoul (or Sylvie maybe, if we implement it)
        self.assertEqual(len(record), 1)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
        "odoo.tests",
    )
    def test_message_process_alias_followers_multiemail(self):
        """Incoming email from a parent document follower on a Followers only
        alias depends on email_from / partner recognition, to be tested when
        dealing with multi emails / formatted emails."""
        self.alias.write(
            {
                "alias_contact": "followers",
                "alias_parent_model_id": self.env["ir.model"]
                ._get("mail.test.gateway")
                .id,
                "alias_parent_thread_id": self.test_record.id,
            }
        )
        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        email_from = formataddr(("Another Name", self.partner_1.email_normalized))

        for partner_email, passed in [
            (formataddr((self.partner_1.name, self.partner_1.email_normalized)), True),
            (
                f'{self.partner_1.email_normalized}, "Multi Email" <multi.email@test.example.com>',
                True,
            ),
            (
                f'"Multi Email" <multi.email@test.example.com>, {self.partner_1.email_normalized}',
                False,
            ),
        ]:
            with self.subTest(partner_email=partner_email):
                self.partner_1.write({"email": partner_email})
                record = self.format_and_process(
                    MAIL_TEMPLATE,
                    email_from,
                    f"groups@{self.alias_domain}",
                    subject=f"Test for {partner_email}",
                )

                if passed:
                    self.assertEqual(len(record), 1)
                    self.assertEqual(record.email_from, email_from)
                    self.assertFalse(
                        record.message_partner_ids,
                        "Non internal are not added as followers when being post authors",
                    )
                # multi emails not recognized (no normalized email, recognition)
                else:
                    self.assertEqual(
                        len(record),
                        0,
                        "Alias check (FIXME): multi-emails bad support for recognition",
                    )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
    )
    def test_message_process_alias_update(self):
        """Incoming email update discussion + notification email"""
        self.alias.write({"alias_force_thread_id": self.test_record.id})

        self.test_record.message_subscribe(partner_ids=[self.partner_1.id])
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                msg_id="<1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>",
                subject="Re: cats",
            )

        # Test: no new group + new message
        self.assertFalse(
            record, "message_process: alias update should not create new records"
        )
        self.assertEqual(len(self.test_record.message_ids), 2)
        # Test: sent emails: 1 (Sylvie copy of the incoming email)
        self.assertSentEmail(self.email_from, [self.partner_1], subject="Re: cats")

    # --------------------------------------------------
    # Creator recognition
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_create_uid_crash(self):
        def _employee_crash(records, operation):
            """If employee is test employee, consider they have no access on document"""
            if records.env.uid == self.user_employee.id and not records.env.su:
                return lambda: exceptions.AccessError(
                    "Hop hop hop Ernest, please step back."
                ), records
            return DEFAULT

        with patch.object(
            MailTestGateway, "check_access", autospec=True, side_effect=_employee_crash
        ):
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.user_employee.email_formatted,
                f"groups@{self.alias_domain}",
                subject="NoEmployeeAllowed",
            )
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, "NoEmployeeAllowed")
        self.assertEqual(
            record.message_ids[0].create_uid,
            self.user_root,
            "Message should be created by caller of message_process.",
        )
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_create_uid_email(self):
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.user_employee.email_formatted,
            f"groups@{self.alias_domain}",
            subject="Email Found",
        )
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, "Email Found")
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

        record = self.format_and_process(
            MAIL_TEMPLATE,
            f"Another name <{self.user_employee.email}>",
            f"groups@{self.alias_domain}",
            subject="Email OtherName",
        )
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, "Email OtherName")
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.user_employee.email_normalized,
            f"groups@{self.alias_domain}",
            subject="Email SimpleEmail",
        )
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, "Email SimpleEmail")
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
    )
    def test_message_process_create_uid_email_follower(self):
        self.alias.write(
            {
                "alias_parent_model_id": self.env["ir.model"]._get_id(
                    self.test_record._name
                ),
                "alias_parent_thread_id": self.test_record.id,
            }
        )
        follower_user = mail_new_test_user(
            self.env,
            login="better",
            groups="base.group_user",
            name="Ernest Follower",
            email=self.user_employee.email,
        )
        self.test_record.message_subscribe(follower_user.partner_id.ids)

        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.user_employee.email_formatted,
            f"groups@{self.alias_domain}",
            subject="FollowerWinner",
        )
        self.assertEqual(record.create_uid, follower_user)
        self.assertEqual(record.message_ids[0].subject, "FollowerWinner")
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, follower_user.partner_id)

        # name order win
        self.test_record.message_unsubscribe(follower_user.partner_id.ids)
        self.test_record.flush_recordset()
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.user_employee.email_formatted,
            f"groups@{self.alias_domain}",
            subject="FirstFoundWinner",
        )
        self.assertEqual(record.create_uid, self.user_employee)
        self.assertEqual(record.message_ids[0].subject, "FirstFoundWinner")
        self.assertEqual(record.message_ids[0].create_uid, self.user_root)
        self.assertEqual(record.message_ids[0].author_id, self.user_employee.partner_id)

    # --------------------------------------------------
    # Alias routing management
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_no_domain(self):
        """Incoming email: write to alias with no domain set: not recognized as
        a valid alias even when local-part only is checked."""
        self.alias.alias_domain_id = False

        for incoming_ok in [True, False]:
            with self.subTest(incoming_ok=incoming_ok):
                with self.assertRaises(ValueError):
                    _new_record = self.format_and_process(
                        MAIL_TEMPLATE,
                        self.partner_1.email_formatted,
                        f"groups@{self.alias_domain}",
                        subject="Test Subject",
                    )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_alias_incoming_local(self):
        """Incoming email: write to alias using local part only: depends on
        alias accepting local only flag."""
        self.alias.alias_incoming_local = True
        new_record = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            "groups@another.domain.com",
            subject="Test Subject Global",
        )
        self.assertEqual(
            len(new_record),
            1,
            "message_process: a new mail.test.simple should have been created",
        )

        self.alias.alias_incoming_local = False
        with self.assertRaises(ValueError):
            _new_record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                "groups@another.domain.com",
                subject="Test Subject Local",
            )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_forward_bypass_reply_first(self):
        """Incoming email: write to two "new thread" alias, one as a reply, one being another model -> consider as a forward"""
        self.assertEqual(len(self.test_record.message_ids), 1)

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test",
                "alias_model_id": self.env["ir.model"]._get("mail.test.container").id,
                "alias_contact": "everyone",
            }
        )
        new_rec = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"{new_alias_2.display_name}, {self.alias.display_name}",
            subject="Test Subject",
            extra=f"In-Reply-To:\r\n\t{self.fake_email.message_id}\n",
            target_model=new_alias_2.alias_model_id.model,
        )
        # Forward created a new record in mail.test
        self.assertEqual(
            len(new_rec), 1, "message_process: a new mail.test should have been created"
        )
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        # No new post on test_record, no new record in mail.test.simple either
        self.assertEqual(
            len(self.test_record.message_ids),
            1,
            "message_process: should not post on replied record as forward should bypass it",
        )
        new_simple = self.env["mail.test.simple"].search(
            [("name", "=", "Test Subject")]
        )
        self.assertEqual(
            len(new_simple),
            0,
            "message_process: a new mail.test should not have been created",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_forward_bypass_reply_second(self):
        """Incoming email: write to two "new thread" alias, one as a reply, one being another model -> consider as a forward"""
        self.assertEqual(len(self.test_record.message_ids), 1)

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test",
                "alias_model_id": self.env["ir.model"]._get("mail.test.container").id,
                "alias_contact": "everyone",
            }
        )
        new_rec = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"{self.alias.display_name}, {new_alias_2.display_name}",
            subject="Test Subject",
            extra=f"In-Reply-To:\r\n\t{self.fake_email.message_id}\n",
            target_model=new_alias_2.alias_model_id.model,
        )
        # Forward created a new record in mail.test
        self.assertEqual(
            len(new_rec), 1, "message_process: a new mail.test should have been created"
        )
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        # No new post on test_record, no new record in mail.test.simple either
        self.assertEqual(
            len(self.test_record.message_ids),
            1,
            "message_process: should not post on replied record as forward should bypass it",
        )
        new_simple = self.env["mail.test.simple"].search(
            [("name", "=", "Test Subject")]
        )
        self.assertEqual(
            len(new_simple),
            0,
            "message_process: a new mail.test should not have been created",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_forward_bypass_update_alias(self):
        """Incoming email: write to one "update", one "new thread" alias, one as a reply, one being another model -> consider as a forward"""
        self.assertEqual(len(self.test_record.message_ids), 1)
        self.alias.write(
            {
                "alias_force_thread_id": self.test_record.id,
            }
        )

        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test",
                "alias_model_id": self.env["ir.model"]._get("mail.test.container").id,
                "alias_contact": "everyone",
            }
        )
        new_rec = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"{new_alias_2.display_name}, {self.alias.display_name}",
            subject="Test Subject",
            extra=f"In-Reply-To:\r\n\t{self.fake_email.message_id}\n",
            target_model=new_alias_2.alias_model_id.model,
        )
        # Forward created a new record in mail.test
        self.assertEqual(
            len(new_rec), 1, "message_process: a new mail.test should have been created"
        )
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        # No new post on test_record, no new record in mail.test.simple either
        self.assertEqual(
            len(self.test_record.message_ids),
            1,
            "message_process: should not post on replied record as forward should bypass it",
        )
        # No new record on first alias model
        new_simple = self.env["mail.test.gateway"].search(
            [("name", "=", "Test Subject")]
        )
        self.assertEqual(
            len(new_simple),
            0,
            "message_process: a new mail.test should not have been created",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_multiple_new(self):
        """Incoming email: write to two aliases creating records: both should be activated"""
        # test@.. will cause the creation of new mail.test
        new_alias_2 = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test",
                "alias_model_id": self.env["ir.model"]._get("mail.test.container").id,
                "alias_contact": "everyone",
            }
        )
        new_rec = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"{self.alias.display_name}, {new_alias_2.display_name}",
            subject="Test Subject",
            target_model=new_alias_2.alias_model_id.model,
        )
        # New record in both mail.test (new_alias_2) and mail.test.simple (self.alias)
        self.assertEqual(
            len(new_rec), 1, "message_process: a new mail.test should have been created"
        )
        self.assertEqual(new_rec._name, new_alias_2.alias_model_id.model)
        new_simple = self.env["mail.test.gateway"].search(
            [("name", "=", "Test Subject")]
        )
        self.assertEqual(
            len(new_simple),
            1,
            "message_process: a new mail.test should have been created",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_alias_with_allowed_domains(self):
        """Incoming email: check that if domains are set in the optional system
        parameter `mail.catchall.domain.allowed` only incoming emails from these
        domains will generate records."""
        # test@.. will cause the creation of new mail.test.container
        new_alias_2 = self.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain_id": self.mail_alias_domain_c2.id,
                "alias_incoming_local": True,
                "alias_model_id": self.env["ir.model"]._get_id(
                    "mail.test.container.mc"
                ),
                "alias_name": "test",
            }
        )

        test_domain = "hello.com"
        for (alias_right_part, allowed_domain), container_created in zip(
            [
                # Test a valid alias domain, standard case
                (self.mail_alias_domain_c2.name, ""),
                # Test with 'mail.catchall.domain.allowed' not set in system parameters
                # and with a domain not allowed
                ("bonjour.com", ""),
                # Test with 'mail.catchall.domain.allowed' set in system parameters
                # and with a domain not allowed
                ("bonjour.com", test_domain),
                # Test with 'mail.catchall.domain.allowed' set in system parameters
                # and with a domain allowed
                (test_domain, test_domain),
            ],
            [True, True, False, True],
            strict=True,
        ):
            with self.subTest(
                alias_right_part=alias_right_part, allowed_domain=allowed_domain
            ):
                self.env["ir.config_parameter"].set_param(
                    "mail.catchall.domain.allowed", allowed_domain
                )

                subject = f"Test wigh {alias_right_part}-{allowed_domain}"
                email_to = f"{self.alias.alias_name}@{self.alias_domain}, {new_alias_2.alias_name}@{alias_right_part}"

                self.format_and_process(
                    MAIL_TEMPLATE,
                    self.partner_1.email_formatted,
                    email_to,
                    subject=subject,
                    target_model=self.alias.alias_model_id.model,
                )

                res_alias_1 = self.env["mail.test.gateway"].search(
                    [("name", "=", subject)]
                )
                res_alias_2 = self.env["mail.test.container.mc"].search(
                    [("name", "=", subject)]
                )
                self.assertTrue(
                    bool(res_alias_1), "First alias should always be respected"
                )
                self.assertEqual(bool(res_alias_2), container_created)

    # --------------------------------------------------
    # Email Management
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_bounce(self):
        """Incoming email: bounce  using bounce alias: no record creation"""
        with self.mock_mail_gateway():
            new_recs = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"{self.alias_bounce}@{self.alias_domain}",
                subject="Should bounce",
            )
        self.assertFalse(new_recs)
        self.assertNotSentEmail()

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_bounce_other_recipients(self):
        """Incoming email: bounce processing: bounce should be computed even if not first recipient"""
        with self.mock_mail_gateway():
            new_recs = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"{self.alias.alias_name}@{self.alias_domain}, {self.alias_bounce}@{self.alias_domain}",
                subject="Should bounce",
            )
        self.assertFalse(new_recs)
        self.assertNotSentEmail()

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.models.mail_mail",
        "odoo.models.unlink",
    )
    def test_message_route_write_to_catchall(self):
        """Writing directly to catchall should bounce"""
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f'"My Super Catchall" <{self.alias_catchall}@{self.alias_domain}',
                subject="Should Bounce",
            )
        self.assertFalse(record)
        self.assertSentEmail(
            self.mailer_daemon_email,
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Should Bounce",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_write_to_catchall_uses_the_written_to_company(self):
        """A bounce speaks for the company whose catchall was written to."""
        other_company = self.env["res.company"].create(
            {"name": "Second Co", "email": "contact@second.example.com"}
        )
        other_domain = self.env["mail.alias.domain"].create(
            {"name": "second.example.com", "catchall_alias": "catchall"}
        )
        other_company.alias_domain_id = other_domain
        self.assertEqual(other_domain.company_ids[:1], other_company)
        self.assertNotEqual(self.env.company, other_company)

        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f'"Their Catchall" <{other_domain.catchall_email}>',
                subject="Should Bounce For Second Co",
            )
        self.assertFalse(record)
        bounce = self._new_mails[0]
        self.assertIn(
            other_company.name,
            bounce.body_html,
            "the bounce must name the company owning the catchall written to",
        )
        self.assertEqual(bounce.reply_to, other_company.email)

    def test_message_route_write_to_catchall_other_recipients_first(self):
        """Writing directly to catchall and a valid alias should take alias"""
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"{self.alias_catchall}@{self.alias_domain}, {self.alias.alias_name}@{self.alias_domain}",
                subject="Catchall Not Blocking",
            )
        # Test: one group created
        self.assertEqual(
            len(record), 1, "message_process: a new mail.test should have been created"
        )
        # No bounce email
        self.assertNotSentEmail()

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_route_write_to_catchall_other_recipients_second(self):
        """Writing directly to catchall and a valid alias should take alias"""
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f"{self.alias.alias_name}@{self.alias_domain}, {self.alias_catchall}@{self.alias_domain}",
                subject="Catchall Not Blocking",
            )
        # Test: one group created
        self.assertEqual(
            len(record), 1, "message_process: a new mail.test should have been created"
        )
        # No bounce email
        self.assertNotSentEmail()

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.models.mail_mail",
        "odoo.models.unlink",
    )
    def test_message_route_write_to_catchall_other_recipients_invalid(self):
        """Writing to catchall and other unroutable recipients should bounce."""
        # Test: no group created, email bounced
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                f'"My Super Catchall" <{self.alias_catchall}@{self.alias_domain}>, Unroutable <unroutable@{self.alias_domain}>',
                subject="Should Bounce",
            )
        self.assertFalse(record)
        self.assertSentEmail(
            self.mailer_daemon_email,
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Should Bounce",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_alias(self):
        """Writing to bounce alias is considered as a bounce even if not multipart/report bounce structure"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounce_email_to = f"{self.alias_bounce}@{self.alias_domain}"
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            bounce_email_to,
            subject="Undelivered Mail Returned to Sender",
        )
        self.assertFalse(record)
        # No information found in bounce email -> not possible to do anything except avoiding email
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_from_mailer_demon(self):
        """MAILER_DAEMON emails are considered as bounce"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        record = self.format_and_process(
            MAIL_TEMPLATE,
            "MAILER-DAEMON@example.com",
            f"groups@{self.alias_domain}",
            subject="Undelivered Mail Returned to Sender",
        )
        self.assertFalse(record)
        # No information found in bounce email -> not possible to do anything except avoiding email
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_missing_final_recipient(self):
        """The Final-Recipient header is missing, the partner must be found thanks to the original mail message."""
        email = test_mail_data.MAIL_BOUNCE.replace("Final-Recipient", "XX")
        email = email.replace("Original-Recipient", "XX")

        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        # no notification to find, won't be able to find the correct recipient
        extra = self.fake_email.message_id
        record = self.format_and_process(
            email,
            self.partner_1.email_formatted,
            f"{self.alias_bounce}@{self.alias_domain}",
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        # the partner will be found in the <mail.notification> res_partner_id
        extra = self.fake_email.message_id
        self.env["mail.notification"].create(
            {
                "res_partner_id": self.partner_1.id,
                "mail_message_id": self.fake_email.id,
            }
        )
        record = self.format_and_process(
            email,
            self.partner_1.email_formatted,
            f"{self.alias_bounce}@{self.alias_domain}",
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 1)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_multipart_alias(self):
        """Multipart/report bounce correctly make related partner bounce"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounce_email_to = f"{self.alias_bounce}@{self.alias_domain}"
        record = self.format_and_process(
            test_mail_data.MAIL_BOUNCE,
            self.partner_1.email_formatted,
            bounce_email_to,
            subject="Undelivered Mail Returned to Sender",
        )
        self.assertFalse(record)
        # Missing in reply to message_id -> cannot find original record
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_multipart_alias_reply(self):
        """Multipart/report bounce correctly make related partner and record found in bounce email bounce"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        notification = self.env["mail.notification"].create(
            {
                "mail_message_id": self.fake_email.id,
                "res_partner_id": self.partner_1.id,
            }
        )

        bounce_email_to = f"{self.alias_bounce}@{self.alias_domain}"
        extra = self.fake_email.message_id
        record = self.format_and_process(
            test_mail_data.MAIL_BOUNCE,
            self.partner_1.email_formatted,
            bounce_email_to,
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 1)
        self.assertIn(
            "This is the mail system at host mail2.test.ironsky.",
            notification.failure_reason,
            msg="Should store the bounce email body on the notification",
        )
        self.assertEqual(notification.failure_type, "mail_bounce")
        self.assertEqual(notification.notification_status, "bounce")

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_multipart_alias_whatever_from(self):
        """Multipart/report bounce correctly make related record found in bounce email bounce"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        bounce_email_to = f"{self.alias_bounce}@{self.alias_domain}"
        extra = self.fake_email.message_id
        record = self.format_and_process(
            test_mail_data.MAIL_BOUNCE,
            "Whatever <what@ever.com>",
            bounce_email_to,
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 1)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_multipart_whatever_to_and_from(self):
        """Multipart/report bounce correctly make related record found in bounce email bounce"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

        extra = self.fake_email.message_id
        record = self.format_and_process(
            test_mail_data.MAIL_BOUNCE,
            "Whatever <what@ever.com>",
            f"groups@{self.alias_domain}",
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 1)

        # The local part of the FROM is not "MAILER-DAEMON", and the Content type is slightly
        # different. Thanks to the report type, it still should be detected as a bounce email.
        email = test_mail_data.MAIL_BOUNCE.replace(
            "multipart/report;", "multipart/report:"
        )
        email = email.replace(
            "MAILER-DAEMON@mail2.test.ironsky", "email@mail2.test.ironsky"
        )
        self.assertIn("report-type=delivery-status", email)
        extra = self.fake_email.message_id
        record = self.format_and_process(
            email,
            "Whatever <what@ever.com>",
            f"groups@{self.alias_domain}",
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 2)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_not_bounce_spoofed_report_type(self):
        """A non-report content-type carrying a report-type=delivery-status
        param (or a boundary embedding that token) must NOT be treated as a
        bounce: an attacker could otherwise get any mail to a public alias
        silently dropped. Only the multipart/report maintype is a bounce
        signal; the report-type param on its own is not (read receipts carry
        report-type=disposition-notification on multipart/report).
        """
        # a normal message whose Content-Type gained a spoofed report-type param
        spoofed = MAIL_TEMPLATE.replace(
            "Content-Type: multipart/alternative;",
            "Content-Type: multipart/alternative; report-type=delivery-status;",
        )
        self.assertIn("report-type=delivery-status", spoofed)
        record = self.format_and_process(
            spoofed,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Not a bounce",
        )
        self.assertEqual(
            len(record), 1, "spoofed report-type must not suppress record creation"
        )
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
    )
    def test_message_process_bounce_records_channel(self):
        """Test blacklist allow to multi-bounce and auto update of discuss.channel"""
        other_record = self.env["mail.test.gateway"].create(
            {"email_from": f"Another name <{self.partner_1.email}>"}
        )
        yet_other_record = self.env["mail.test.gateway"].create(
            {"email_from": f"Yet Another name <{self.partner_1.email.upper()}>"}
        )
        test_channel = self.env["discuss.channel"].create(
            {
                "name": "Test",
                "channel_partner_ids": [(4, self.partner_1.id)],
                "group_public_id": None,
            }
        )
        self.fake_email.write(
            {
                "model": "discuss.channel",
                "res_id": test_channel.id,
            }
        )
        self.assertIn(self.partner_1, test_channel.channel_partner_ids)
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.assertEqual(other_record.message_bounce, 0)
        self.assertEqual(yet_other_record.message_bounce, 0)

        extra = self.fake_email.message_id
        for _i in range(10):
            record = self.format_and_process(
                test_mail_data.MAIL_BOUNCE,
                f"A third name <{self.partner_1.email}>",
                f"groups@{self.alias_domain}",
                subject="Undelivered Mail Returned to Sender",
                extra=extra,
            )
            self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 10)
        self.assertEqual(self.test_record.message_bounce, 0)
        self.assertEqual(other_record.message_bounce, 10)
        self.assertEqual(yet_other_record.message_bounce, 10)
        # MAX_BOUNCE_LIMIT in discuss_channel is set to 10,
        # If this partner exceeds the limit, remove them from the channel.
        self.assertNotIn(self.partner_1, test_channel.channel_partner_ids)

        # On a new successful incoming email, the partner bounce counter should be reset.
        self.format_and_process(
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"groups@{self.alias_domain}",
            subject="Test Working Email Subject",
            extra=f"In-Reply-To:\r\n\t{self.fake_email.message_id}\n",
        )
        self.assertEqual(self.partner_1.message_bounce, 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_records_partner(self):
        """Test blacklist + bounce on ``res.partner`` model"""
        self.assertEqual(self.partner_1.message_bounce, 0)
        self.fake_email.write(
            {
                "model": "res.partner",
                "res_id": self.partner_1.id,
            }
        )

        extra = self.fake_email.message_id
        record = self.format_and_process(
            test_mail_data.MAIL_BOUNCE,
            self.partner_1.email_formatted,
            f"groups@{self.alias_domain}",
            subject="Undelivered Mail Returned to Sender",
            extra=extra,
        )
        self.assertFalse(record)
        self.assertEqual(self.partner_1.message_bounce, 1)
        self.assertEqual(self.test_record.message_bounce, 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_bounce_records_partner_multi(self):
        """Bounce must only affect the notification matching the bounced email."""

        bounce_email = "specific.bounce.address@example.com"

        message = self._create_gateway_message(
            self.test_record,
            "bounce_multi",
            body="Test message",
            message_type="email",
            partner_ids=(self.partner_1 + self.partner_employee).ids,
            subject="Test Multi Partner",
        )

        notif_partner, notif_employee = self.env["mail.notification"].create(
            [
                {
                    "mail_message_id": message.id,
                    "res_partner_id": self.partner_1.id,
                    "notification_type": "email",
                    "notification_status": "sent",
                    "mail_email_address": bounce_email,
                },
                {
                    "mail_message_id": message.id,
                    "res_partner_id": self.partner_employee.id,
                    "notification_type": "email",
                    "notification_status": "sent",
                },
            ]
        )

        with self.mock_mail_gateway():
            self.format_and_process(
                test_mail_data.MAIL_BOUNCE,
                bounce_email,
                f"groups@{self.alias_domain}",
                subject="Undelivered Mail Returned to Sender",
                extra=message.message_id,
            )

        self.assertEqual(notif_partner.notification_status, "bounce")
        self.assertEqual(notif_employee.notification_status, "sent")

    # --------------------------------------------------
    # Thread formation
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
        "odoo.tests",
    )
    def test_message_process_external_notification_reply(self):
        """Ensure responses bot messages are discussions."""
        bot_notification_message = self._create_gateway_message(
            self.test_record,
            "bot_notif_message",
            author_id=self.env.ref("base.partner_root").id,
            message_type="auto_comment",
            is_internal=True,
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            "",
            subject="Reply to bot notif",
            extra=f"References: {bot_notification_message.message_id}",
        )
        new_msg = self.test_record.message_ids[0]
        self.assertFalse(
            new_msg.is_internal,
            "Responses to messages sent by odoobot should always be public.",
        )
        self.assertEqual(new_msg.parent_id, bot_notification_message)
        self.assertEqual(new_msg.subtype_id, self.env.ref("mail.mt_comment"))

        # Also check the regular case
        some_notification_message = self._create_gateway_message(
            self.test_record,
            "some_notif_message",
            message_type="notification",
            is_internal=True,
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            "",
            subject="Reply to some notif",
            extra=f"References: {some_notification_message.message_id}",
        )
        new_msg = self.test_record.message_ids[0]
        self.assertTrue(
            new_msg.is_internal,
            "Responses to messages sent by anyone but odoobot should keep"
            "the 'is_internal' value of the parent.",
        )
        self.assertEqual(new_msg.parent_id, some_notification_message)
        self.assertEqual(new_msg.subtype_id, self.env.ref("mail.mt_note"))

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_in_reply_to(self):
        """Incoming email using in-rely-to should go into the right destination even with a wrong destination"""
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE,
            "valid.other@gmail.com",
            f"erroneous@{self.alias_domain}",
            subject="Re: news",
            extra=f"In-Reply-To:\r\n\t{self.fake_email.message_id}\n",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_references(self):
        """Incoming email using references should go into the right destination even with a wrong destination"""
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"erroneous@{self.alias_domain}",
            extra=f"References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
        "odoo.tests",
    )
    def test_message_process_references_multi_parent(self):
        """Incoming email with multiple references"""
        alias_update = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_force_thread_id": self.test_record.id,
                "alias_name": "test.update",
                "alias_model_id": self.env["ir.model"]._get(self.test_record._name).id,
                "alias_contact": "everyone",
            }
        )
        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            reply1 = self._create_gateway_message(
                self.test_record,
                "reply1",
                parent_id=self.fake_email.id,
            )
            reply2 = self._create_gateway_message(
                self.test_record,
                "reply2",
                parent_id=self.fake_email.id,
                subtype_id=self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
            )
            reply1_1 = self._create_gateway_message(
                self.test_record,
                "reply1_1",
                parent_id=reply1.id,
                subtype_id=self.env["ir.model.data"]._xmlid_to_res_id("mail.mt_note"),
            )
            reply2_1 = self._create_gateway_message(
                self.test_record,
                "reply2_1",
                parent_id=reply2.id,
            )

        # reply to reply1 using multiple references
        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Reply to reply1",
                extra=f"References: {reply1.message_id} {self.fake_email.message_id}",
            )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(
            new_msg.parent_id, reply1, "Newer parent found should be selected"
        )
        self.assertEqual(
            new_msg.subtype_id,
            self.env.ref("mail.mt_comment"),
            "Mail: reply to a comment should be a comment",
        )

        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"test.gateway@{self.alias_domain}",
                subject="Reply to reply1_1 (with noise)",
                extra=f"References: {reply1_1.message_id} {reply1.message_id} {reply1.message_id}",
            )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(
            new_msg.parent_id, reply1_1, "Newer parent found should be selected"
        )
        self.assertEqual(
            new_msg.subtype_id,
            self.env.ref("mail.mt_note"),
            "Mail: reply to a note should be a note",
        )

        # ordering should not impact
        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Reply to reply1 (order issue)",
                extra=f"References: {self.fake_email.message_id} {reply1.message_id}",
            )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(
            new_msg.parent_id, reply1, "Mail: flattening attach to original message"
        )
        self.assertEqual(
            new_msg.subtype_id,
            self.env.ref("mail.mt_comment"),
            "Mail: reply to a comment should be a comment",
        )

        # history with last one being a note
        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Reply to reply1_1",
                extra=f"References: {reply1_1.message_id} {self.fake_email.message_id}",
            )
        new_msg = self.test_record.message_ids[0]
        self.assertEqual(
            new_msg.parent_id, reply1_1, "Mail: flattening attach to original message"
        )
        self.assertEqual(
            new_msg.subtype_id,
            self.env.ref("mail.mt_note"),
            "Mail: reply to a note should be a note",
        )

        # messed up history (two child branches): gateway initial parent is newest one
        with (
            self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)),
            self.mock_mail_gateway(),
            self.mock_mail_app(),
        ):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Reply to reply2_1 (with noise)",
                date=datetime(2025, 11, 20, 10, 30, 0),
                extra=f"References: {reply1_1.message_id} {reply2_1.message_id}",
            )
        new_msg = self._new_msgs
        self.assertEqual(new_msg, self.test_record.message_ids[0])
        self.assertEqual(new_msg.date, datetime(2025, 11, 20, 10, 30, 0))
        self.assertEqual(
            new_msg.parent_id, reply2_1, "Mail: flattening attach to original message"
        )
        self.assertEqual(
            new_msg.subtype_id,
            self.env.ref("mail.mt_comment"),
            "Mail: parent should be a comment",
        )

        # no references: new discussion thread started. Alias allows to post on
        # a record without replying, aka without references, which means parent
        # set to last email / discussion message
        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            old_msg = self._create_gateway_message(
                self.test_record,
                "old_msg",
                date=datetime(2024, 11, 20, 10, 30, 0),
                parent_id=reply1.id,
            )
        self.assertEqual(old_msg.date, datetime(2024, 11, 20, 10, 30, 0))
        with self.mock_datetime_and_now(datetime(2024, 11, 20, 10, 30, 0)):
            old_disturbing_msg = self._create_gateway_message(
                self.test_record,
                "old_disturbinh_msg",
                date=False,
                parent_id=reply1.id,
            )
        self.assertFalse(old_disturbing_msg.date)

        with self.mock_datetime_and_now(datetime(2025, 11, 19, 10, 30, 0)):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                alias_update.alias_full_name,
                subject="New thread",
                extra="References:",
            )
        last_msg = self.test_record.message_ids[0]
        self.assertEqual(
            last_msg.parent_id,
            new_msg,
            "No free message, attached to last thread comment / email",
        )
        self.assertEqual(
            last_msg.subtype_id,
            self.env.ref("mail.mt_comment"),
            "Mail: parent should be a comment",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
        "odoo.tests",
    )
    def test_message_process_references_multi_parent_notflat(self):
        """Incoming email with multiple references with ``_mail_flat_thread``
        being False (mail.group/discuss.channel behavior like)."""
        test_record = self.env["mail.test.gateway.groups"].create(
            {
                "alias_name": "test.gateway",
                "name": "Test",
                "email_from": "ignasse@example.com",
            }
        )

        # Set a first message on public group to test update and hierarchy
        first_msg = self._create_gateway_message(test_record, "first_msg")
        reply1 = self._create_gateway_message(
            test_record,
            "reply1",
            parent_id=first_msg.id,
        )

        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"test.gateway@{self.alias_domain}",
            subject="Reply to reply1",
            extra=f"References: {first_msg.id} {reply1.message_id}",
        )
        new_msg = test_record.message_ids[0]
        self.assertEqual(
            new_msg.parent_id,
            reply1,
            "Mail: pseudo no flattening: getting up one level (reply1 parent)",
        )
        self.assertEqual(
            new_msg.subtype_id,
            self.env.ref("mail.mt_comment"),
            "Mail: parent should be a comment",
        )

        # no references: new discussion thread started
        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"test.gateway@{self.alias_domain}",
            subject="New thread",
            extra="References:",
        )
        new_thread = test_record.message_ids[0]
        self.assertFalse(
            new_thread.parent_id,
            "Mail: pseudo no flattening: no parent means new thread",
        )
        self.assertEqual(new_thread.subject, "New thread")
        self.assertEqual(
            new_thread.subtype_id,
            self.env.ref("mail.mt_comment"),
            "Mail: parent should be a comment",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_references_external(self):
        """Incoming email being a reply to an external email processed by odoo should update thread accordingly"""
        new_message_id = "<ThisIsTooMuchFake.MonsterEmail.789@agrolait.com>"
        self.fake_email.write({"message_id": new_message_id})
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"erroneous@{self.alias_domain}",
            extra=f"References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_references_external_buggy_message_id(self):
        """
        Incoming email being a reply to an external email processed by
        odoo should update thread accordingly. Special case when the
        external mail service wrongly folds the message_id on several
        lines.
        """
        new_message_id = "<ThisIsTooMuchFake.MonsterEmail.789@agrolait.com>"
        buggy_message_id = new_message_id.replace("MonsterEmail", "Monster\r\n  Email")
        self.fake_email.write({"message_id": new_message_id})
        init_msg_count = len(self.test_record.message_ids)
        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"erroneous@{self.alias_domain}",
            extra=f"References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {buggy_message_id}",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(self.fake_email.child_ids, self.test_record.message_ids[0])

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_references_forward(self):
        """Incoming email using references but with alias forward should not go into references destination"""
        self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test.alias",
                "alias_model_id": self.env["ir.model"]._get("mail.test.container").id,
                "alias_contact": "everyone",
            }
        )
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"test.alias@{self.alias_domain}",
            subject="My Dear Forward",
            extra=f"References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}",
            target_model="mail.test.container",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count)
        self.assertEqual(len(self.fake_email.child_ids), 0)
        self.assertEqual(res_test.name, "My Dear Forward")
        self.assertEqual(len(res_test.message_ids), 1)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_references_forward_same_model(self):
        """Incoming email using references but with alias forward on same model should be considered as a reply"""
        self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test.alias",
                "alias_model_id": self.env["ir.model"]._get("mail.test.gateway").id,
                "alias_contact": "everyone",
            }
        )
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"test.alias@{self.alias_domain}",
            subject="My Dear Forward",
            extra=f"References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}",
            target_model="mail.test.container",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(len(self.fake_email.child_ids), 1)
        self.assertFalse(res_test)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_references_forward_cc(self):
        """Incoming email using references but with alias forward in CC should be considered as a repy (To > Cc)"""
        self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test.alias",
                "alias_model_id": self.env["ir.model"]._get("mail.test.container").id,
                "alias_contact": "everyone",
            }
        )
        init_msg_count = len(self.test_record.message_ids)
        res_test = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"{self.alias_catchall}@{self.alias_domain}",
            cc=f"test.alias@{self.alias_domain}",
            subject="My Dear Forward",
            extra=f"References: <2233@a.com>\r\n\t<3edss_dsa@b.com> {self.fake_email.message_id}",
            target_model="mail.test.container",
        )

        self.assertEqual(len(self.test_record.message_ids), init_msg_count + 1)
        self.assertEqual(len(self.fake_email.child_ids), 1)
        self.assertFalse(res_test)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models.unlink",
        "odoo.addons.mail.models.mail_mail",
    )
    def test_message_process_reply_to_new_thread(self):
        """Test replies not being considered as replies but use destination information instead (aka, mass post + specific reply to using aliases)"""
        first_record = (
            self.env["mail.test.simple"]
            .with_user(self.user_employee)
            .create({"name": "Replies to Record"})
        )
        record_msg = first_record.message_post(
            subject="Discussion",
            reply_to_force_new=False,
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(
            record_msg.reply_to,
            formataddr(
                (
                    self.partner_employee.name,
                    f"{self.alias_catchall}@{self.alias_domain}",
                )
            ),
        )
        mail_msg = first_record.message_post(
            subject="Replies to Record",
            reply_to=f"groups@{self.alias_domain}",
            reply_to_force_new=True,
            subtype_xmlid="mail.mt_comment",
        )
        self.assertEqual(mail_msg.reply_to, f"groups@{self.alias_domain}")

        # reply to mail but should be considered as a new mail for alias
        msgID = "<this.is.duplicate.test@iron.sky>"
        res_test = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            record_msg.reply_to,
            cc="",
            subject="Re: Replies to Record",
            extra=f"In-Reply-To: {record_msg.message_id}",
            msg_id=msgID,
            target_model="mail.test.simple",
        )
        incoming_msg = self.env["mail.message"].search([("message_id", "=", msgID)])
        self.assertFalse(res_test)
        self.assertEqual(incoming_msg.model, "mail.test.simple")
        self.assertEqual(incoming_msg.parent_id, record_msg)
        self.assertTrue(incoming_msg.res_id == first_record.id)

        # reply to mail but should be considered as a new mail for alias
        msgID = "<this.is.for.testing@iron.sky>"
        res_test = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            mail_msg.reply_to,
            cc="",
            subject="Re: Replies to Record",
            extra=f"In-Reply-To: {mail_msg.message_id}",
            msg_id=msgID,
            target_model="mail.test.gateway",
        )
        incoming_msg = self.env["mail.message"].search([("message_id", "=", msgID)])
        self.assertEqual(len(res_test), 1)
        self.assertEqual(res_test.name, "Re: Replies to Record")
        self.assertEqual(incoming_msg.model, "mail.test.gateway")
        self.assertFalse(incoming_msg.parent_id)
        self.assertTrue(incoming_msg.res_id == res_test.id)

    # --------------------------------------------------
    # Gateway / Record synchronization
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_gateway_values_base64_image(self):
        """New record with mail that contains base64 inline image."""
        target_model = "mail.test.field.type"
        alias = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "base64-lover",
                "alias_model_id": self.env["ir.model"]._get(target_model).id,
                "alias_defaults": "{}",
                "alias_contact": "everyone",
            }
        )
        record = self.format_and_process(
            test_mail_data.MAIL_TEMPLATE_EXTRA_HTML,
            self.email_from,
            f"{alias.alias_name}@{self.alias_domain}",
            subject="base64 image to alias",
            target_model=target_model,
            extra_html='<img src="data:image/png;base64,iV/+OkI=">',
        )
        self.assertEqual(record.type, "first")
        self.assertEqual(len(record.message_ids[0].attachment_ids), 1)
        self.assertEqual(record.message_ids[0].attachment_ids[0].name, "image0")
        self.assertEqual(record.message_ids[0].attachment_ids[0].type, "binary")

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_gateway_values_base64_image_walias(self):
        """New record with mail that contains base64 inline image + default values
        coming from alias."""
        target_model = "mail.test.field.type"
        alias = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "base64-lover",
                "alias_model_id": self.env["ir.model"]._get(target_model).id,
                "alias_defaults": "{'type': 'second'}",
                "alias_contact": "everyone",
            }
        )
        record = self.format_and_process(
            test_mail_data.MAIL_TEMPLATE_EXTRA_HTML,
            self.email_from,
            f"{alias.alias_name}@{self.alias_domain}",
            subject="base64 image to alias",
            target_model=target_model,
            extra_html='<img src="data:image/png;base64,iV/+OkI=">',
        )
        self.assertEqual(record.type, "second")
        self.assertEqual(len(record.message_ids[0].attachment_ids), 1)
        self.assertEqual(record.message_ids[0].attachment_ids[0].name, "image0")
        self.assertEqual(record.message_ids[0].attachment_ids[0].type, "binary")

    # --------------------------------------------------
    # Thread formation: mail gateway corner cases
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_extra_model_res_id(self):
        """Incoming email with ref holding model / res_id but that does not match any message in the thread: must raise since Odoo saas-3"""
        self.assertRaises(
            ValueError,
            self.format_and_process,
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"noone@{self.alias_domain}",
            subject="spam",
            extra=f"In-Reply-To: <12321321-odoo-{self.test_record.id}-{self.test_record._name}@{socket.gethostname()}>",
        )

        # when 6.1 messages are present, compat mode is available
        # Odoo 10 update: compat mode has been removed and should not work anymore
        self.fake_email.write({"message_id": False})
        # Do: compat mode accepts partial-matching emails
        self.assertRaises(
            ValueError,
            self.format_and_process,
            MAIL_TEMPLATE,
            self.partner_1.email_formatted,
            f"noone@{self.alias_domain}>",
            subject="spam",
            extra=f"In-Reply-To: <12321321-odoo-{self.test_record.id}-mail.test.gateway@{socket.gethostname()}>",
        )

        # Test created messages
        self.assertEqual(len(self.test_record.message_ids), 1)
        self.assertEqual(len(self.test_record.message_ids[0].child_ids), 0)

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_duplicate(self):
        """Duplicate emails (same message_id) are not processed"""
        self.alias.write(
            {
                "alias_force_thread_id": self.test_record.id,
            }
        )

        # Post a base message
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Re: super cats",
            msg_id="<123.456.diff1@agrolait.com>",
        )
        self.assertFalse(record)
        self.assertEqual(len(self.test_record.message_ids), 2)

        # Do: due to some issue, same email goes back into the mailgateway
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"groups@{self.alias_domain}",
            subject="Re: news",
            msg_id="<123.456.diff1@agrolait.com>",
            extra="In-Reply-To: <1198923581.41972151344608186799.JavaMail.diff1@agrolait.com>\n",
        )
        self.assertFalse(record)
        self.assertEqual(len(self.test_record.message_ids), 2)

        # Test: message_id is still unique
        no_of_msg = self.env["mail.message"].search_count(
            [("message_id", "ilike", "<123.456.diff1@agrolait.com>")]
        )
        self.assertEqual(
            no_of_msg,
            1,
            "message_process: message with already existing message_id should not have been duplicated",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_crash_wrong_model(self):
        """Incoming email with model that does not accepts incoming emails must raise"""
        self.assertRaises(
            ValueError,
            self.format_and_process,
            MAIL_TEMPLATE,
            self.email_from,
            f"noone@{self.alias_domain}",
            subject="spam",
            extra="",
            model="res.country",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_crash_no_data(self):
        """Incoming email without model and without alias must raise"""
        self.assertRaises(
            ValueError,
            self.format_and_process,
            MAIL_TEMPLATE,
            self.email_from,
            f"noone@{self.alias_domain}",
            subject="spam",
            extra="",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_message_process_fallback(self):
        """Incoming email with model that accepting incoming emails as fallback"""
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"noone@{self.alias_domain}",
            subject="Spammy",
            extra="",
            model="mail.test.gateway",
        )
        self.assertEqual(len(record), 1)
        self.assertEqual(record.name, "Spammy")
        self.assertEqual(record._name, "mail.test.gateway")

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_file_encoding(self):
        """Incoming email with file encoding"""
        file_content = "Hello World"
        for encoding in ["", "UTF-8", "UTF-16LE", "UTF-32BE", "cp-850"]:
            file_content_b64 = base64.b64encode(
                file_content.encode(encoding or "utf-8")
            ).decode()
            record = self.format_and_process(
                test_mail_data.MAIL_FILE_ENCODING,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject=f"Test Charset {encoding or 'Unset'}",
                charset=f'; charset="{encoding}"' if encoding else "",
                content=file_content_b64,
            )
            attachment = record.message_ids.attachment_ids
            self.assertEqual(file_content, attachment.raw.decode(encoding or "utf-8"))
            if encoding not in ["", "UTF-8", "cp-850"]:
                self.assertNotEqual(file_content, attachment.raw.decode("utf-8"))

    def test_message_hebrew_iso8859_8_i(self):
        # This subject was found inside an email of one of our customer.
        # The charset is iso-8859-8-i which isn't natively supported by
        # python, check that Odoo is still capable of decoding it.
        subject = "בוקר טוב! צריך איימק ושתי מסכים"
        encoded_subject = (
            "=?iso-8859-8-i?B?4eX3+CDo5eEhIPb46eog4Onp7vcg5fn66SDu8evp7Q==?="
        )

        # This content was made up using google translate. The charset
        # is iso-8859-8 which is natively supported by python.
        charset = "iso-8859-8"
        content = "שלום וברוכים הבאים למקרה המבחן הנפלא הזה"
        encoded_content = base64.b64encode(content.encode(charset)).decode()

        with RecordCapturer(self.env["mail.test.gateway"]) as capture:
            mail = test_mail_data.MAIL_FILE_ENCODING.format(
                msg_id="<test_message_hebrew_iso8859_8_i@iron.sky>",
                subject=encoded_subject,
                charset=f'; charset="{charset}"',
                content=encoded_content,
            )
            self.env["mixin.mail.thread"].message_process("mail.test.gateway", mail)

        capture.records.check_singleton()
        self.assertEqual(capture.records.name, subject)
        self.assertEqual(
            capture.records.message_ids.attachment_ids.raw.decode(charset), content
        )

    def test_message_windows_874(self):
        # Email for Thai customers who use Microsoft email service.
        # The charset is windows-874 which isn't natively supported by
        # python, check that Odoo is still capable of decoding it.
        # windows-874 is the Microsoft equivalent of cp874.
        with (
            self.mock_mail_gateway(),
            RecordCapturer(self.env["mail.test.gateway"]) as capture,
        ):
            self.env["mixin.mail.thread"].message_process(
                "mail.test.gateway", THAI_EMAIL_WINDOWS_874
            )
        capture.records.check_singleton()
        self.assertEqual(capture.records.name, "เรื่อง")
        self.assertEqual(str(capture.records.message_ids.body), "<pre>ร่างกาย</pre>\n")

    # --------------------------------------------------
    # Corner cases / Bugs during message process
    # --------------------------------------------------

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_file_encoding_ascii(self):
        """Incoming email containing an xml attachment with unknown characters (�) but an ASCII charset should not
        raise an Exception. UTF-8 is used as a safe fallback.
        """
        record = self.format_and_process(
            test_mail_data.MAIL_MULTIPART_INVALID_ENCODING,
            self.email_from,
            f"groups@{self.alias_domain}",
        )

        self.assertEqual(
            record.message_ids.attachment_ids.name,
            "bis3_with_error_encoding_address.xml",
        )
        # NB: the xml received by email contains b"Chauss\xef\xbf\xbd\xef\xbf\xbde" with "\xef\xbf\xbd" being the
        # replacement character � in UTF-8.
        # When calling `_message_parse_extract_payload`, `part.get_content()` will be called on the attachment part of
        # the email, triggering the decoding of the base64 attachment, so b"Chauss\xef\xbf\xbd\xef\xbf\xbde" is
        # first retrieved. Then, `get_text_content` in `email` tries to decode this using the charset of the email
        # part, i.e: `content.decode('us-ascii', errors='replace')`. So the errors are replaced using the Unicode
        # replacement marker and the string "Chauss������e" is used to create the attachment.
        # This explains the multiple "�" in the attachment.
        self.assertIn(
            "Chauss������e de Bruxelles", record.message_ids.attachment_ids.raw.decode()
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_file_omitted_charset_xml(self):
        """For incoming email containing an xml attachment with omitted charset and containing an UTF8 payload we
        should parse the attachment using UTF-8.
        """
        record = self.format_and_process(
            test_mail_data.MAIL_MULTIPART_OMITTED_CHARSET_XML,
            self.email_from,
            f"groups@{self.alias_domain}",
        )
        self.assertEqual(record.message_ids.attachment_ids.name, "bis3.xml")
        self.assertEqual(
            "<Invoice>Chaussée de Bruxelles</Invoice>",
            record.message_ids.attachment_ids.raw.decode(),
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_file_omitted_charset_csv(self):
        """For incoming email containing a csv attachment with omitted charset and containing an UTF8 payload we
        should parse the attachment using UTF-8.
        """
        record = self.format_and_process(
            test_mail_data.MAIL_MULTIPART_OMITTED_CHARSET_CSV,
            self.email_from,
            f"groups@{self.alias_domain}",
        )
        self.assertEqual(record.message_ids.attachment_ids.name, "bis3.csv")
        self.assertEqual(
            "\ufeffAuftraggeber;LieferadresseStraße;",
            record.message_ids.attachment_ids.raw.decode(),
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_process_file_omitted_charset_txt(self):
        """For incoming email containing a txt attachment with omitted charset and containing an UTF8 payload we
        should parse the attachment using UTF-8.
        """
        test_string = (
            "Äpfel und Birnen sind Früchte, die im Herbst geerntet werden. In der Nähe des Flusses steht ein großes, "
            "altes Schloss. Über den Dächern sieht man oft Vögel fliegen. Müller und Schröder sind typische deutsche Nachnamen. "
            "Die Straße, in der ich wohne, heißt „Bachstraße“ und ist sehr ruhig. Überall im Wald wachsen Bäume mit kräftigen Ästen. "
            "Können wir uns über die Pläne für das nächste Wochenende unterhalten?"
        )
        record = self.format_and_process(
            test_mail_data.MAIL_MULTIPART_OMITTED_CHARSET_TXT,
            self.email_from,
            f"groups@{self.alias_domain}",
        )
        self.assertEqual(record.message_ids.attachment_ids.name, "bis3.txt")
        self.assertEqual(test_string, record.message_ids.attachment_ids.raw.decode())

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_route_reply_model_none(self):
        """
        Test the message routing and reply functionality when the model is None.

        This test case verifies the behavior of the message routing and reply process
        when the 'model' field of a mail.message is set to None. It checks that the
        message is correctly processed and associated with the appropriate record.
        The code invokes function `format_and_process` to automatically test rounting
        and then makes checks on created record.

        """
        message = self.env["mail.message"].create(
            {
                "body": "<p>test</p>",
                "email_from": self.email_from,
                "message_type": "email_outgoing",
                "model": None,
                "res_id": None,
            }
        )

        self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_name": "test",
                "alias_model_id": self.env["ir.model"]._get("mail.test.gateway").id,
            }
        )
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"test@{self.alias_domain}",
            subject=message.message_id,
            extra=f"In-Reply-To:\r\n\t{message.message_id}\n",
            model=None,
        )

        self.assertTrue(record)
        self.assertEqual(record._name, "mail.test.gateway")
        self.assertEqual(record.message_ids.subject, message.message_id)
        self.assertFalse(record.message_ids.parent_id)


@tagged("mail_gateway", "mail_loop")
class TestMailGatewayLoops(MailGatewayCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("mail.gateway.loop.minutes", 30)
        cls.env["ir.config_parameter"].sudo().set_param(
            "mail.gateway.loop.threshold", 5
        )

        cls.env["mail.gateway.allowed"].create(
            [
                {"email": "Bob@EXAMPLE.com"},
                {"email": '"Alice From Example" <alice@EXAMPLE.com>'},
                {"email": '"Eve From Example" <eve@EXAMPLE.com>'},
            ]
        )

        cls.alias_ticket = cls.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain_id": cls.mail_alias_domain.id,
                "alias_model_id": cls.env["ir.model"]._get_id("mail.test.ticket"),
                "alias_name": "test.ticket",
            }
        )
        cls.alias_other = cls.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain_id": cls.mail_alias_domain.id,
                "alias_model_id": cls.env["ir.model"]._get_id("mail.test.gateway"),
                "alias_name": "test.gateway",
            }
        )

        # recipients
        cls.customer_email = "customer@test.example.com"
        cls.alias_partner, cls.other_partner = cls.env["res.partner"].create(
            [
                {
                    "email": f'"Stupid Idea" <{cls.alias_other.alias_name}@{cls.alias_other.alias_domain}>',
                    "name": "Stupid Idea",
                },
                {
                    "email": '"Other Customer" <other.customer@test.example.com>',
                    "name": "Other Customer",
                },
            ]
        )

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    @patch.object(Cursor, "now", lambda *args, **kwargs: datetime(2022, 1, 1, 10, 0, 0))
    def test_routing_loop_alias_create(self):
        """Test the limit on the number of record we can create by alias."""
        # Send an email 2 hours ago, should not have an impact on more recent emails
        with patch.object(
            Cursor, "now", lambda *args, **kwargs: datetime(2022, 1, 1, 8, 0, 0)
        ):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"{self.alias_ticket.alias_name}@{self.alias_domain}",
                subject="Test alias loop old",
                target_model=self.alias_ticket.alias_model_id.model,
            )

        for i in range(5):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"{self.alias_ticket.alias_name}@{self.alias_domain}",
                subject=f"Test alias loop {i}",
                target_model=self.alias_ticket.alias_model_id.model,
            )

        records = self.env["mail.test.ticket"].search(
            [("name", "ilike", "Test alias loop %")]
        )
        self.assertEqual(len(records), 6, "Should have created 6 <mail.test.gateway>")
        self.assertEqual(
            set(records.mapped("email_from")),
            {self.email_from},
            msg="Should have automatically filled the email field",
        )

        for email_from, exp_to in [
            (
                self.email_from,
                formataddr(("Sylvie Lelitre", "test.sylvie.lelitre@agrolait.com")),
            ),
            (
                self.email_from.upper(),
                formataddr(("SYLVIE LELITRE", "test.sylvie.lelitre@agrolait.com")),
            ),
        ]:
            with self.mock_mail_gateway():
                self.format_and_process(
                    MAIL_TEMPLATE,
                    email_from,
                    f"{self.alias_ticket.alias_name}@{self.alias_domain}",
                    subject="Test alias loop X",
                    target_model=self.alias_ticket.alias_model_id.model,
                    return_path=email_from,
                )

            new_record = self.env["mail.test.ticket"].search(
                [("name", "=", "Test alias loop X")]
            )
            self.assertFalse(
                new_record,
                msg="The loop should have been detected and the record should not have been created",
            )

            self.assertSentEmail(
                f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>', [exp_to]
            )
            bounce_references = self._mails[0]["references"]
            self.assertIn(
                "-loop-detection-bounce-email@",
                bounce_references,
                msg='The "bounce email" tag must be in the reference',
            )

        # The reply to the bounce email must be ignored
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                "alice@example.com",  # whitelisted from, should be taken into account
                f"{self.alias_ticket.alias_name}@{self.alias_domain}",
                subject="Test alias loop X",
                target_model=self.alias_ticket.alias_model_id.model,
                return_path=self.email_from,
                extra=f"References: {bounce_references}",
            )
        self.assertNotSentEmail()

        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                "alice@example.com",  # whitelisted from, should be taken into account
                f"{self.alias_ticket.alias_name}@{self.alias_domain}",
                subject="Test alias loop X",
                target_model=self.alias_ticket.alias_model_id.model,
                return_path=self.email_from,
                extra=f"In-Reply-To: {bounce_references}",
            )
        self.assertNotSentEmail()

        # Email address in the whitelist should not have the restriction
        for i in range(10):
            self.format_and_process(
                MAIL_TEMPLATE,
                "alice@example.com",
                f"{self.alias_ticket.alias_name}@{self.alias_domain}",
                subject=f"Whitelist test alias loop {i}",
                target_model=self.alias_ticket.alias_model_id.model,
            )
        records = self.env["mail.test.ticket"].search(
            [("name", "ilike", "Whitelist test alias loop %")]
        )
        self.assertEqual(
            len(records), 10, msg="Email whitelisted should not have the restriction"
        )

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    def test_routing_loop_alias_mix(self):
        """Test loop detection in case of multiples routes, just be sure all
        routes are checked and models checked once."""
        # create 2 update-records aliases and 1 new-record alias on same model
        test_updates = self.env["mail.test.gateway.groups"].create(
            [
                {
                    "alias_name": "test.update1",
                    "name": "Update1",
                },
                {
                    "alias_name": "test.update2",
                    "name": "Update2",
                },
            ]
        )
        alias_gateway_group, alias_ticket_other = self.env["mail.alias"].create(
            [
                {
                    "alias_contact": "everyone",
                    "alias_model_id": self.env["ir.model"]._get_id(
                        "mail.test.gateway.groups"
                    ),
                    "alias_name": "test.new",
                },
                {
                    "alias_contact": "everyone",
                    "alias_model_id": self.env["ir.model"]._get_id("mail.test.ticket"),
                    "alias_name": "test.ticket.other",
                },
            ]
        )

        _original_ticket_sc = MailTestTicket.search_count
        _original_groups_sc = MailTestGatewayGroups.search_count
        _original_rgr = MailMessage._read_group
        with (
            self.mock_mail_gateway(),
            patch.object(
                MailTestTicket,
                "search_count",
                autospec=True,
                side_effect=_original_ticket_sc,
            ) as mock_ticket_sc,
            patch.object(
                MailTestGatewayGroups,
                "search_count",
                autospec=True,
                side_effect=_original_groups_sc,
            ) as mock_groups_sc,
            patch.object(
                MailMessage, "_read_group", autospec=True, side_effect=_original_rgr
            ) as mock_msg_rgr,
        ):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.other_partner.email_formatted,
                f'"Super Help" <{self.alias_ticket.alias_name}@{self.alias_ticket.alias_domain}>,'
                f"{test_updates[0].alias_id.display_name}, {test_updates[1].alias_id.display_name}, "
                f"{alias_gateway_group.display_name}, {alias_ticket_other.display_name}",
                subject="Valid Inquiry",
                return_path=self.other_partner.email_formatted,
                target_model="mail.test.ticket",
            )
        self.assertEqual(
            mock_ticket_sc.call_count,
            1,
            "Two alias creating tickets but one check anyway",
        )
        self.assertEqual(mock_groups_sc.call_count, 1, "One alias creating groups")
        self.assertEqual(
            mock_msg_rgr.call_count,
            1,
            "Only one model updating records, one call even if two aliases",
        )
        self.assertEqual(
            len(self.env["mail.test.ticket"].search([("name", "=", "Valid Inquiry")])),
            2,
            "One by creating alias, as no loop was detected",
        )

        # create 'looping' history by pre-creating messages on a thread -> should block future incoming emails
        self.env["mail.message"].create(
            [
                {
                    "author_id": self.other_partner.id,
                    "model": test_updates[0]._name,
                    "res_id": test_updates[0].id,
                    "message_type": "email",
                }
                for x in range(4)  # 4 + 1 posted before = 5 aka threshold
            ]
        )
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.other_partner.email_formatted,
                f'"Super Help" <{self.alias_ticket.alias_name}@{self.alias_ticket.alias_domain}>,'
                f"{test_updates[0].alias_id.display_name}, {test_updates[1].alias_id.display_name}, "
                f"{alias_gateway_group.display_name}, {alias_ticket_other.display_name}",
                subject="Looping Inquiry",
                return_path=self.other_partner.email_formatted,
                target_model="mail.test.ticket",
            )
        self.assertFalse(
            self.env["mail.test.ticket"].search([("name", "=", "Looping Inquiry")]),
            "Even if other routes are ok, one looping route is sufficient to block the incoming email",
        )

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    def test_routing_loop_auto_notif(self):
        """Test Odoo servers talking to each other"""
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.other_partner.email_formatted,
                f'"Super Help" <{self.alias_ticket.alias_name}@{self.alias_ticket.alias_domain}>',
                subject="Inquiry",
                return_path=self.other_partner.email_formatted,
                target_model="mail.test.ticket",
            )
        self.assertTrue(record)

        for incoming_count in range(6):  # threshold + 1
            with self.mock_mail_gateway():
                record.with_user(self.user_employee).message_post(
                    body="Automatic answer",
                    message_type="auto_comment",
                    partner_ids=self.other_partner.ids,
                    subtype_xmlid="mail.mt_comment",
                )
            capture_messages = self.gateway_mail_reply_last_email(MAIL_TEMPLATE)
            msg = capture_messages.records
            self.assertTrue(msg)
            # first messages are accepted -> post a message on record
            if incoming_count < 4:  # which makes 5 accepted messages
                self.assertIn(msg, record.message_ids)
            # other attempts triggers only a bounce
            else:
                self.assertFalse(msg.model)
                self.assertFalse(msg.res_id)
                self.assertIn(
                    "loop-detection-bounce-email",
                    msg.mail_ids.references,
                    "Should be a msg linked to a bounce email with right header",
                )

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    def test_routing_loop_follower_alias(self):
        """Use case: managing follower that are aliases."""
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                f'"Annoying Customer" <{self.customer_email}>',
                f'"Super Help" <{self.alias_ticket.alias_name}@{self.alias_ticket.alias_domain}>',
                cc=f"{self.alias_partner.email_normalized}, {self.other_partner.email_normalized}",
                subject="Inquiry",
                return_path=self.customer_email,
                target_model="mail.test.ticket",
            )
        self.assertEqual(record.name, "Inquiry")
        self.assertFalse(record.message_partner_ids, "Inquiry")
        self.assertNotSentEmail()
        self.assertEqual(
            record.message_ids.partner_ids,
            self.other_partner,
            "MailGateway: recipients = alias should not be linked to message",
        )

        # for some stupid reason, people add an alias as follower
        with self.mock_mail_gateway():
            _message = record.with_user(self.user_employee).message_post(
                body="Answer",
                partner_ids=self.alias_partner.ids,
            )
        self.assertSentEmail(
            self.user_employee.email_formatted, [self.alias_partner.email_formatted]
        )

        # simulate this email coming back to the same Odoo server -> msg_id is
        # a duplicate, hence rejected
        with (
            RecordCapturer(self.env["mail.test.ticket"]) as capture_ticket,
            RecordCapturer(self.env["mail.test.gateway"]) as capture_gateway,
        ):
            self._reinject()
        self.assertFalse(capture_ticket.records)
        self.assertFalse(capture_gateway.records)
        self.assertNotSentEmail()
        self.assertFalse(bool(self._new_msgs))

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    def test_routing_loop_forward_catchall(self):
        """Use case: broad email forward to catchall. Example: customer sends an
        email to catchall. It bounces: to=customer, return-path=bounce. Autoreply
        replies to bounce: to=bounce. It is forwarded to catchall. It bounces,
        and hop we have a loop."""
        customer_email = "customer@test.example.com"

        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                f'"Annoying Customer" <{customer_email}>',
                f'"No Reply" <{self.alias_catchall}@{self.alias_domain}>, Unroutable <unroutable@{self.alias_domain}>',
                subject="Should Bounce (initial)",
                return_path=customer_email,
            )
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            [customer_email],
            subject="Re: Should Bounce (initial)",
        )
        original_mail = self._mails

        # auto-reply: write to bounce = no more bounce
        self.gateway_mail_reply_last_email(
            MAIL_TEMPLATE, force_email_to=f"{self.alias_bounce}@{self.alias_domain}"
        )
        self.assertNotSentEmail()

        # auto-reply but forwarded to catchall -> should not bounce again
        self._mails = original_mail  # just to revert state prior to auto reply
        self.gateway_mail_reply_last_email(
            MAIL_TEMPLATE, force_email_to=f"{self.alias_catchall}@{self.alias_domain}"
        )
        # TDE FIXME: this should not bounce again
        # self.assertNotSentEmail()
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            [customer_email],
            subject="Re: Re: Re: Should Bounce (initial)",
        )


@tagged("mail_gateway")
class TestMailGatewayHelpers(MailGatewayCommon):
    """The routing helpers exercised as functions, not through a whole email.

    Everything else in this file reaches them by building a message and running
    `message_process` -- 135 times over. That is the right test for routing *as
    a whole* and the wrong one for a rule inside it: a broken threshold fails
    somewhere far from its cause, and some of these rules cannot be reached that
    way at all without twenty round-trips per assertion.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.thread_model = cls.env["mixin.mail.thread"]

    # ------------------------------------------------------------------
    # loop detection
    # ------------------------------------------------------------------

    def _mails_on(self, record, count, author=None, email_from=False):
        """`count` incoming-email messages on one record, as the gateway logs them."""
        self.env["mail.message"].sudo().create(
            [
                {
                    "author_id": author.id if author else False,
                    "email_from": email_from,
                    "message_type": "email",
                    "model": record._name,
                    "res_id": record.id,
                    "subtype_id": self.env.ref("mail.mt_comment").id,
                }
                for _ in range(count)
            ]
        )

    def test_loop_replies_are_counted_per_document_not_across_them(self):
        """Twenty mails over twenty tickets is twenty conversations; twenty on
        one ticket is a loop. Reaching this through `message_process` would take
        forty round-trips to distinguish the two."""
        records = self.env["mail.test.gateway"].create(
            [{"name": f"Loop {index}"} for index in range(4)]
        )
        author = self.partner_1
        limit = self.env.cr.now() - timedelta(minutes=120)

        # 5 each across four documents: twenty mails, no loop at a threshold of 5
        for record in records:
            self._mails_on(record, 4, author=author)
        self.assertFalse(
            records._has_loop_sender_replied_too_often(
                records.ids, "a@b.example.com", "a@b.example.com", author.id, limit, 5
            ),
            "sixteen mails spread over four documents is not a loop",
        )

        # one more on a single document tips only that one over
        self._mails_on(records[0], 1, author=author)
        self.assertTrue(
            records._has_loop_sender_replied_too_often(
                records.ids, "a@b.example.com", "a@b.example.com", author.id, limit, 5
            ),
            "five on one document is a loop even when the others are quiet",
        )

    def test_loop_replies_match_the_address_when_there_is_no_author(self):
        """An unknown external sender leaves no partner, so the raw address is
        the only handle -- and it is the branch a known-author test never runs."""
        record = self.env["mail.test.gateway"].create({"name": "Anon"})
        limit = self.env.cr.now() - timedelta(minutes=120)
        self._mails_on(record, 3, email_from="stranger@remote.example.org")
        self.assertTrue(
            record._has_loop_sender_replied_too_often(
                record.ids,
                "stranger@remote.example.org",
                "stranger@remote.example.org",
                False,
                limit,
                3,
            )
        )
        self.assertFalse(
            record._has_loop_sender_replied_too_often(
                record.ids,
                "someone.else@remote.example.org",
                "someone.else@remote.example.org",
                False,
                limit,
                3,
            ),
            "another sender's mails are not this sender's loop",
        )

    def test_loop_creation_is_only_asked_when_a_route_would_create(self):
        """The creation counter is skipped entirely when every route names an
        existing document -- it is the auto-responder-makes-a-record loop."""
        record = self.env["mail.test.gateway"].create({"name": "Existing"})
        limit = self.env.cr.now() - timedelta(minutes=120)
        self.assertFalse(
            record._has_loop_sender_created_too_many(
                [record.id], "a@b.example.com", limit, 0
            ),
            "a threshold of zero still does not fire when nothing would be created",
        )

    # ------------------------------------------------------------------
    # the target check
    # ------------------------------------------------------------------

    def _target(self, model, thread_id, raise_exception=False):
        route = Route(model, thread_id, None, self.env.uid, None)
        return self.thread_model._routing_check_target(
            {"message_id": "<probe@x>"}, route, raise_exception
        )

    def test_target_rejects_a_model_that_cannot_hold_a_document(self):
        for model, why in (
            ("", "no model at all"),
            ("no.such.model", "unknown model"),
            ("mixin.mail.thread", "abstract model"),
            ("res.lang", "model that is not a thread"),
        ):
            with self.subTest(model=model):
                self.assertIsNone(self._target(model, False), why)

    def test_a_reply_naming_an_unusable_model_is_refused_not_crashed(self):
        """`_routing_check_route` unpacks whatever the target check hands back,
        so a rejection spelled `()` instead of `None` raised `not enough values
        to unpack` right here. The reply route is the one that reaches it: it
        passes `raise_exception=False`, so nothing raises earlier, and its model
        comes from a `References` header -- an uninstalled module or a hand-
        written reference is all it takes.
        """
        for model in ("", "no.such.model", "mixin.mail.thread", "res.lang"):
            with self.subTest(model=model):
                self.assertIs(
                    self.env["mixin.mail.thread"]._routing_check_route(
                        None,  # only consulted when the route names an alias
                        {"message_id": "<probe@x>", "email_from": "a@b.example.com"},
                        Route(model, 1, None, self.env.uid, None),
                        raise_exception=False,
                    ),
                    RouteVerdict.UNUSABLE,
                    "an unusable model is a refused route, not an exception",
                )

    def test_target_falls_back_to_creation_when_the_reply_target_is_gone(self):
        """A `thread_id` of None on the way out is not a rejection -- it means
        the message should start a document instead of updating one."""
        record = self.env["mail.test.gateway"].create({"name": "Doomed"})
        record_id = record.id
        record.unlink()
        target = self._target("mail.test.gateway", record_id)
        self.assertIsNotNone(target, "a deleted target does not kill the route")
        self.assertIsNone(target[1], "it falls back to creating a document")

    def test_target_returns_the_document_when_the_reply_target_exists(self):
        record = self.env["mail.test.gateway"].create({"name": "Alive"})
        record_set, thread_id = self._target("mail.test.gateway", record.id)
        self.assertEqual(record_set, record)
        self.assertEqual(thread_id, record.id)

    # ------------------------------------------------------------------
    # bounce parsing
    # ------------------------------------------------------------------

    def _dsn(self, final_recipient):
        """A `message/delivery-status` part, notice first and fields second."""
        return email.message_from_string(
            "Content-Type: message/delivery-status\r\n\r\n"
            "Reporting-MTA: dns; mta.example.com\r\n\r\n"
            f"{final_recipient}\r\n",
            policy=email.policy.SMTP,
        )

    def test_post_params_drop_gateway_state_and_refuse_a_collision(self):
        """The dict the parser fills and the arguments `message_post` takes are
        not the same set, and the gateway has to subtract before it can splat.

        The subtraction is a hand-maintained list, so the interesting case is the
        one it does not cover: a parsed key that collides with a value the router
        computes. That used to surface as `dict(subtype_id=..., **parsed)` raising
        `TypeError: got multiple values for keyword argument` from a line that
        does not look like a check.
        """
        gateway = self.env["mixin.mail.thread"]
        parsed = {
            "message_id": "<params@example.com>",
            "body": "<p>hello</p>",
            "author_id": self.partner_1.id,
            # gateway working state, all of it stripped
            "to": "a@b.com",
            "cc": "c@d.com",
            "from": "e@f.com",
            "recipients": "a@b.com",
            "references": "",
            "in_reply_to": "",
            "is_bounce": False,
            "author_lookups": {("mixin.mail.thread", False): False},
        }
        params = gateway._message_route_post_params(
            dict(parsed),
            incoming_email_to="a@b.com",
            incoming_email_cc="c@d.com",
            subtype_id=self.env.ref("mail.mt_comment").id,
            partner_ids=[],
        )
        self.assertEqual(params["body"], "<p>hello</p>")
        self.assertEqual(params["author_id"], self.partner_1.id)
        self.assertEqual(params["incoming_email_to"], "a@b.com")
        for stripped in gateway._GATEWAY_ONLY_MESSAGE_KEYS:
            self.assertNotIn(
                stripped, params, f"{stripped} is gateway state, not a message value"
            )

        with self.assertRaises(ValueError) as caught:
            gateway._message_route_post_params(
                dict(parsed, subtype_id=1),
                incoming_email_to=False,
                incoming_email_cc=False,
                subtype_id=self.env.ref("mail.mt_note").id,
                partner_ids=[],
            )
        self.assertIn("subtype_id", str(caught.exception))
        self.assertIn("<params@example.com>", str(caught.exception))

    def test_the_parent_author_is_added_when_a_reply_would_not_reach_them(self):
        """`partner_ids` on this path is the lever `_notify_thread` reads, not a
        recipient list: it carries the parent message's author so that a reply
        reaches whoever wrote what is being replied to.

        Two ways a reply would otherwise miss them. An internal note notifies
        followers, and the author of the note may not be one. And an *external*
        author -- `partner_share`, a customer or a portal user -- is not reached
        by the internal-facing half of a notification either, whatever the
        subtype. An internal author on a public message needs no lever: the
        ordinary follower path already reaches them.
        """
        external_author = self.partner_1
        self.assertTrue(external_author.partner_share, "the premise of this test")
        internal_author = self.user_employee.partner_id
        self.assertFalse(internal_author.partner_share, "the premise of this test")

        note = self._create_gateway_message(
            self.test_record, "note", subtype_id=self.env.ref("mail.mt_note").id
        )
        public_external = self._create_gateway_message(self.test_record, "pub-ext")
        public_internal = self._create_gateway_message(
            self.test_record, "pub-int", author_id=internal_author.id
        )
        gateway = self.env["mixin.mail.thread"]
        note_subtype = self.env.ref("mail.mt_note").id
        comment_subtype = self.env.ref("mail.mt_comment").id

        for label, parsed, expected in [
            (
                "a reply to an internal note is a note, and carries its author",
                {"parent_id": note.id, "is_internal": True},
                (note_subtype, [external_author.id]),
            ),
            (
                "an external author is carried on a public message too",
                {"parent_id": public_external.id, "is_internal": False},
                (comment_subtype, [external_author.id]),
            ),
            (
                "an internal author on a public message needs no lever",
                {"parent_id": public_internal.id, "is_internal": False},
                (comment_subtype, []),
            ),
            ("no parent, no lever", {}, (comment_subtype, [])),
        ]:
            with self.subTest(case=label):
                self.assertEqual(
                    gateway._message_route_subtype_and_recipients(parsed, False),
                    expected,
                )

        self.assertEqual(
            gateway._message_route_subtype_and_recipients(
                {"parent_id": note.id, "is_internal": True}, comment_subtype
            ),
            (comment_subtype, [external_author.id]),
            "a created document keeps its own creation subtype",
        )

    def test_a_broken_alias_is_reported_once_per_episode_not_once_per_poll(self):
        """`message_new` raising used to answer a broken alias with a mail loop.

        The bounce goes on a cursor of its own so it survives the rollback the
        caller's `raise` causes -- but `fetchmail_server._deliver` then rolls the
        main cursor back, counts the delivery REFUSED and never calls
        `mark_message_handled`, so the message stays on the server and is offered
        again. The bounce is already committed. Nothing converges: the same
        message fails the same way and bounces again every single poll, and
        neither the duplicate guard (no `mail.message` was committed) nor either
        loop detector (both read the byte-identical *inbound* mail) can see it.

        `alias_status` is the durable state that already tracks this, on the
        right lifecycle: this path sets it, `_alias_mark_valid` clears it as soon
        as a message gets through. What is asserted here is the decision that
        reads it -- the durability itself is the pre-existing separate cursor,
        which a single test transaction cannot exhibit.
        """
        alias = self.env["mail.alias"].create(
            {
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_contact": "everyone",
                "alias_model_id": self.mail_test_gateway_model.id,
                "alias_name": "failing",
            }
        )
        self.registry_enter_test_mode()
        message_dict = {
            "message_id": "<failing-create@example.com>",
            "email_from": self.email_from,
            "to": alias.alias_full_name,
            "references": "",
            "in_reply_to": "",
        }
        message = self.from_string(
            MAIL_TEMPLATE.format(
                to=alias.alias_full_name,
                cc="",
                subject="Breaks on create",
                email_from=self.email_from,
                return_path=self.email_from,
                msg_id=message_dict["message_id"],
                date="Wed, 19 Aug 2026 10:00:00 +0000",
                extra="",
            )
        )
        bounced = []
        real_bounce = MixinMailGateway._routing_bounce_alias

        def counting_bounce(self, bounce_alias, *args, **kwargs):
            bounced.append(bounce_alias.id)
            return real_bounce(self, bounce_alias, *args, **kwargs)

        self.patch(MixinMailGateway, "_routing_bounce_alias", counting_bounce)
        gateway = self.env["mixin.mail.thread"]

        alias.alias_status = "not_tested"
        alias.flush_recordset()  # the bounce cursor reads it in SQL
        gateway._routing_bounce_failed_creation(alias, message, message_dict)
        self.assertEqual(len(bounced), 1, "the first failure is reported")

        alias.alias_status = "invalid"
        alias.flush_recordset()  # the bounce cursor reads it in SQL
        gateway._routing_bounce_failed_creation(alias, message, message_dict)
        self.assertEqual(
            len(bounced),
            1,
            "a second delivery attempt of the same breakage must not bounce "
            "again -- that is the loop this guard exists to stop",
        )

        alias.alias_status = "valid"
        alias.flush_recordset()  # the bounce cursor reads it in SQL
        gateway._routing_bounce_failed_creation(alias, message, message_dict)
        self.assertEqual(
            len(bounced), 2, "an alias that had recovered is reported afresh"
        )

    def test_a_force_new_anchor_is_refused_as_route_and_as_parent(self):
        """`reply_to_force_new` means "a reply to me is not part of my thread".

        Routing has always honoured it, by dropping references minted for it.
        The parent lookup did not, so the same header answered "no thread" to one
        question and "this message" to the other -- and
        `_message_parse_extract_from_parent` reads `is_internal` off whatever it
        gets back, so an external reply could be filed as an internal note on the
        strength of an anchor the router had just refused.
        """
        forced = self._create_gateway_message(
            self.test_record,
            "forced",
            message_id="<0.1234567890-odoo-reply_to@example.com>",
        )
        msg_dict = {"references": forced.message_id, "in_reply_to": ""}
        gateway = self.env["mixin.mail.thread"]
        self.assertFalse(
            gateway._routing_get_replied_message(msg_dict),
            "a forced-new anchor must not decide the route",
        )
        self.assertFalse(
            gateway._get_parent_message(msg_dict),
            "and must not become the parent either",
        )

    def test_an_ordinary_anchor_is_found_from_either_header(self):
        """The unified resolver still answers the question both callers ask, and
        prefers `In-Reply-To` -- which names the direct parent -- over the chain
        that merely contains it."""
        older = self._create_gateway_message(self.test_record, "older")
        newer = self._create_gateway_message(self.test_record, "newer")
        gateway = self.env["mixin.mail.thread"]
        for label, msg_dict, expected in [
            (
                "in-reply-to alone",
                {"references": "", "in_reply_to": older.message_id},
                older,
            ),
            (
                "references alone",
                {"references": newer.message_id, "in_reply_to": ""},
                newer,
            ),
            (
                "in-reply-to wins over the chain",
                {
                    "references": f"{newer.message_id} {older.message_id}",
                    "in_reply_to": older.message_id,
                },
                older,
            ),
        ]:
            with self.subTest(case=label):
                self.assertEqual(
                    gateway._routing_get_replied_message(msg_dict), expected
                )
                self.assertEqual(gateway._get_parent_message(msg_dict), expected)

    def test_a_correspondent_message_id_is_not_mistaken_for_a_forced_one(self):
        """The old test was `"reply_to" not in ref`, which also refused any
        correspondent whose own Message-Id carried the substring."""
        innocent = self._create_gateway_message(
            self.test_record,
            "innocent",
            message_id="<reply_to_me@customer.example.com>",
        )
        msg_dict = {"references": innocent.message_id, "in_reply_to": ""}
        self.assertEqual(
            self.env["mixin.mail.thread"]._routing_get_replied_message(msg_dict),
            innocent,
        )

    def test_bounce_recipient_reads_the_second_dsn_part(self):
        """RFC 3464 puts the human-readable notice first; the per-recipient
        fields are in the part after it."""
        self.env["res.partner"].create(
            {"name": "Bouncer", "email": "gone@remote.example.org"}
        )
        found, partner = self.thread_model._message_parse_bounce_recipient(
            self._dsn("Final-Recipient: rfc822; gone@remote.example.org")
        )
        self.assertEqual(found, "gone@remote.example.org")
        self.assertEqual(partner.email_normalized, "gone@remote.example.org")

    def test_bounce_recipient_survives_a_malformed_report(self):
        """A bounce we cannot attribute is still a bounce: the caller falls back
        to the notification's own recipient rather than seeing an exception."""
        for dsn in (
            None,
            self._dsn("Final-Recipient: no-semicolon-here"),
            self._dsn("Some-Other-Field: nothing useful"),
        ):
            with self.subTest(dsn=dsn):
                found, partner = self.thread_model._message_parse_bounce_recipient(dsn)
                self.assertFalse(found)
                self.assertFalse(partner)

    # ------------------------------------------------------------------
    # part header repair
    # ------------------------------------------------------------------

    def test_unlabelled_utf8_part_decodes_as_sent(self):
        """Without the repair this comes back as us-ascii with replacement
        characters -- the bug is in the *text*, which a count cannot see."""
        part = email.message_from_bytes(
            "Content-Type: text/plain\r\n\r\nCaf\u00e9 na\u00efve\r\n".encode(),
            policy=email.policy.SMTP,
        )
        self.thread_model._message_parse_repair_part_headers(part)
        self.assertEqual(part.get_content().strip(), "Café naïve")

    def test_a_pdf_content_type_that_is_not_a_media_type_is_corrected(self):
        part = email.message_from_string(
            'Content-Type: pdf; name="report.pdf"\r\n\r\nbody\r\n',
            policy=email.policy.SMTP,
        )
        self.thread_model._message_parse_repair_part_headers(part)
        self.assertEqual(part.get_content_type(), "application/pdf")
        self.assertEqual(part.get_param("name"), "report.pdf")


@tagged("mail_gateway")
class TestMailGatewayBounceSender(MailGatewayCommon):
    """A bounce must never be sent `From:` an address we do not own.

    The middle rung of `_routing_get_bounce_from` used to take the inbound `To`
    header verbatim, guarded by a case-sensitive substring test against the
    catchall addresses. A message reaches us with a third party in `To` whenever
    it was Bcc'd or forwarded, and `_is_loop_sender` bounces such messages,
    so the guard being wrong meant sending mail as somebody else's domain.
    """

    def _bounce_from_for(self, email_to):
        message = email.message_from_string(
            f"From: sender@remote.example.org\r\n"
            f"To: {email_to}\r\n"
            f"Subject: hello\r\n\r\nbody\r\n",
            policy=email.policy.SMTP,
        )
        return self.env["mixin.mail.thread"]._routing_get_bounce_from(message)

    def test_bounce_from_prefers_the_configured_bounce_address(self):
        self.assertEqual(
            self._bounce_from_for(f"anything@{self.alias_domain}"),
            formataddr(("MAILER-DAEMON", f"{self.alias_bounce}@{self.alias_domain}")),
        )

    def test_bounce_from_never_uses_a_foreign_recipient(self):
        """The regression: a Bcc'd third party must not become our From."""
        self.env.companies.write({"alias_domain_id": False})
        foreign = "victim@othercompany.example.com"
        bounce_from = self._bounce_from_for(foreign)
        self.assertNotIn(
            "othercompany.example.com",
            bounce_from,
            "a bounce must not be sent from a domain we do not control",
        )
        self.assertIn("MAILER-DAEMON", bounce_from)

    def test_bounce_from_replies_as_our_own_alias(self):
        """The rung is still useful: our own alias is a legitimate sender."""
        self.env.companies.write({"alias_domain_id": False})
        self.assertEqual(
            self._bounce_from_for(f"some.alias@{self.alias_domain}"),
            f"some.alias@{self.alias_domain}",
        )

    def test_bounce_from_matches_the_catchall_case_insensitively(self):
        """The substring test answered False for `CatchAll@Example.com`, so a
        mail to our own catchall in another case took the alias rung."""
        self.env.companies.write({"alias_domain_id": False})
        catchall = f"{self.alias_catchall}@{self.alias_domain}"
        for spelling in (catchall, catchall.upper(), catchall.capitalize()):
            with self.subTest(spelling=spelling):
                self.assertIn(
                    "MAILER-DAEMON",
                    self._bounce_from_for(spelling),
                    "the catchall is never a bounce sender, however it is spelled",
                )


@tagged("mail_gateway", "mail_tools")
class TestMailGatewayRecipients(MailGatewayCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_partners = cls.env["res.partner"].create(
            [
                {
                    "email": '"Test Format" <test.format@test.example.com>',
                    "name": "Format",
                },
                {
                    "email": '"Test Multi" <test.multi@test.example.com>, test.multi.2@test.example.com',
                    "name": "Multi",
                },
                {
                    "email": '"Test Case" <TEST.CASE@test.example.com>',
                    "name": "Case",
                },
            ]
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.models",
    )
    def test_gateway_recipients_finding(self):
        """Incoming email: find or create partners."""
        for additional_to, exp_partners in zip(
            [
                "test.format@test.example.com",
                "TEST.FORMAT@test.example.com",
                '"Another Name" <test.format@test.example.com',
                "test.multi@test.example.com",
                "test.case@test.example.com",
            ],
            [
                self.test_partners[0],
                self.test_partners[0],  # case should not impact
                self.test_partners[0],  # other format should not impact
                self.test_partners[1],
                self.test_partners[
                    2
                ],  # case should not impact (lower versus stored upper)
            ],
            strict=True,
        ):
            with self.subTest(additional_to=additional_to):
                with self.mock_mail_gateway():
                    record = self.format_and_process(
                        MAIL_TEMPLATE,
                        self.email_from,
                        f"{self.alias.alias_full_name}, {additional_to}",
                        subject=f"Test To {additional_to}",
                    )
                self.assertEqual(record.message_ids[0].partner_ids, exp_partners)

                with self.mock_mail_gateway():
                    record = self.format_and_process(
                        MAIL_TEMPLATE,
                        self.email_from,
                        f"{self.alias.alias_full_name}",
                        cc=additional_to,
                        subject=f"Test Cc {additional_to}",
                    )
                self.assertEqual(record.message_ids[0].partner_ids, exp_partners)


@tagged("mail_gateway", "mail_loop", "mail_reply")
class TestMailGatewayReplies(MailGatewayCommon):
    """Check routing of replies, using headers, references, ..."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_employee.notification_type = "email"

        cls.test_records, _partners = cls._create_records_for_batch(
            "mail.test.gateway", 5
        )
        for idx, rec in enumerate(cls.test_records):
            rec.email_from = f"test.gateway.{idx}@test.example.com"

    def test_routing_reply_incoming_email(self):
        """Test routing after receiving starting email on a thread: references
        should include it as it is the "common ancestor" to discussions"""
        with self.mock_mail_gateway():
            gateway_record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                self.alias.display_name,
                subject="Gateway Creation",
            )
        self.assertEqual(len(gateway_record.message_ids), 1)
        gateway_record._message_log(body="Some log")
        with self.mock_mail_gateway():
            gateway_record.with_user(self.user_employee).message_post(
                body="Odoo Reply",
                message_type="comment",
                partner_ids=self.partner_1.ids,
                subtype_id=self.env.ref("mail.mt_comment").id,
            )
        reply, log, email = gateway_record.message_ids
        self.assertMailNotifications(
            reply,
            [
                {
                    "content": "Odoo Reply",
                    "email_values": {
                        "message_id": reply.message_id,
                        "references": f"{email.message_id} {log.message_id} {reply.message_id}",  # should contain reference to OdooExternal message, logs to fill up history
                    },
                    "mail_mail_values": {
                        "notified_partner_ids": self.partner_1,
                        "parent_id": email,  # log serves as thread ancestor
                    },
                    "notif": [
                        {
                            "partner": self.partner_1,
                            "type": "email",
                        },
                    ],
                }
            ],
        )

    def test_routing_reply_internal_messages(self):
        """Test routing notably between two Odoos when internal messages
        are involved. We don't know which message is the ancestor one and
        we should ensure some shared message IDs are present in references
        to help thread formation.

        Action                  Odoo1                   Odoo2
        RFQ-like                                        creation log
                                                        initial_msg
        Odoo2 replies           creation log
                                reply                   reply
        -some internal work-                            user_notification
        Odoo1 replies           reply_2                 reply_2 (incoming email)
        -some internal work-                            log
        Odoo2 replies           reply_3                 reply_3 (outgoing email)

        Purpose: have references from Odoo2 containing message IDs to try to
        correclty route thread.
        """
        gateway_record = self.env["mail.test.gateway"].create(
            {
                "name": "Created through Form",
            }
        )
        gateway_record.message_subscribe(partner_ids=self.partner_admin.ids)
        self.assertEqual(gateway_record.message_partner_ids, self.partner_admin)
        gateway_record.message_post(
            author_id=self.env.ref("base.partner_root").id,
            body="OdooExternal Inquiry",
            email_from=self.partner_1.email_normalized,
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
        )
        self.assertEqual(gateway_record.message_partner_ids, self.partner_admin)
        log, odooext_msg = gateway_record.message_ids[1], gateway_record.message_ids[0]
        self.assertEqual(odooext_msg.parent_id, log, "Log serves as thread ancestor")

        # Odoo2 reply
        with self.mock_mail_gateway():
            gateway_record.with_user(self.user_employee).message_post(
                body="Odoo Reply",
                message_type="comment",
                partner_ids=self.partner_1.ids,
                subtype_id=self.env.ref("mail.mt_comment").id,
            )
        self.assertEqual(
            gateway_record.message_partner_ids,
            self.partner_admin + self.partner_employee,
        )
        reply = gateway_record.message_ids[0]
        self.assertMailNotifications(
            reply,
            [
                {
                    "content": "Odoo Reply",
                    "email_values": {
                        "message_id": reply.message_id,
                        "references": f"{log.message_id} {odooext_msg.message_id} {reply.message_id}",  # should contain reference to OdooExternal message
                    },
                    "mail_mail_values": {
                        "notified_partner_ids": self.partner_1 + self.partner_admin,
                        "parent_id": odooext_msg,  # attached to last comment / email when possible
                    },
                    "notif": [
                        {
                            "partner": self.partner_1,
                            "type": "email",
                        },
                        {
                            "partner": self.partner_admin,
                            "type": "inbox",
                        },
                    ],
                }
            ],
        )

        _user_notif = gateway_record.message_notify(
            body="User Notification",
            partner_ids=self.partner_employee.ids,
            subtype_id=self.env.ref("mail.mt_comment").id,
        )

        # coming from Odoo1: their reply as an incoming email
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                reply.reply_to,
                subject="Gateway Creation",
                date=datetime.now(),
                extra=f"References: {reply.message_id} <msg1@odoo1>",
                debug_log=True,
            )
        reply_2 = gateway_record.message_ids[0]
        self.assertMailNotifications(
            reply_2,
            [
                {
                    "content": "Please call me",
                    "email_values": {
                        "email_from": self.email_from,
                        "message_id": reply_2.message_id,
                        "references": f"{log.message_id} {odooext_msg.message_id} {reply.message_id} {reply_2.message_id}",  # should contain reference to OdooExternal message
                    },
                    "mail_mail_values": {
                        "author_id": self.env["res.partner"],
                        "notified_partner_ids": self.partner_employee
                        + self.partner_admin,
                        "parent_id": reply,
                    },
                    "message_type": "email",
                    "notif": [
                        {
                            "partner": self.partner_employee,
                            "type": "email",
                        },
                        {
                            "partner": self.partner_admin,
                            "type": "inbox",
                        },
                    ],
                }
            ],
        )

        _other_log = gateway_record._message_log(
            body="Internal log",
        )

        with self.mock_mail_gateway():
            gateway_record.with_user(self.user_employee).message_post(
                body="Odoo Reply 2",
                message_type="comment",
                partner_ids=self.partner_1.ids,
                subtype_id=self.env.ref("mail.mt_comment").id,
            )
        self.assertEqual(
            gateway_record.message_partner_ids,
            self.partner_admin + self.partner_employee,
        )
        reply_3 = gateway_record.message_ids[0]
        self.assertMailNotifications(
            reply_3,
            [
                {
                    "content": "Odoo Reply 2",
                    "email_values": {
                        "message_id": reply_3.message_id,
                        "references": f"{odooext_msg.message_id} {reply.message_id} {reply_2.message_id} {reply_3.message_id}",  # should contain reference to OdooExternal message
                    },
                    "mail_mail_values": {
                        "notified_partner_ids": self.partner_1 + self.partner_admin,
                        "parent_id": reply_2,  # attached to last comment / email when possible
                    },
                    "notif": [
                        {
                            "partner": self.partner_1,
                            "type": "email",
                        },
                        {
                            "partner": self.partner_admin,
                            "type": "inbox",
                        },
                    ],
                }
            ],
        )

    @mute_logger(
        "odoo.addons.mail.models.mail_mail",
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
    )
    def test_routing_reply_mailing_references(self):
        """Test mass mailing emails when providers rewrite messageID: references
        should allow to find the original message."""
        # send mailing on records using composer, in both reply and force new modes
        for reply_to_mode, auto_delete_keep_log in [
            ("new", True),
            ("update", True),
            ("new", False),  # reference is lost, but reply alias should be ok
            (
                "update",
                False,
            ),  # reference is lost, hence considered as a reply to catchall, is going to crash (FIXME ?)
        ]:
            with (
                self.subTest(
                    reply_to_mode=reply_to_mode,
                    auto_delete_keep_log=auto_delete_keep_log,
                ),
                self.mock_mail_gateway(mail_unlink_sent=True),
            ):
                composer_form = Form(
                    self.env["mail.compose.message"].with_context(
                        {
                            "active_ids": self.test_records.ids,
                            "default_auto_delete": True,
                            "default_auto_delete_keep_log": auto_delete_keep_log,
                            "default_composition_mode": "mass_mail",
                            "default_email_from": self.user_employee.email_formatted,
                            "default_model": self.test_records._name,
                            "default_subject": "Coucou Hibou",
                        }
                    )
                )
                composer_form.body = '<p>Hello <t t-out="object.name"/></p>'
                composer_form.reply_to_mode = reply_to_mode
                if reply_to_mode == "new":
                    composer_form.reply_to = self.alias.display_name
                composer = composer_form.save()
                mails, _msg = composer._action_send_mail()
                self.assertFalse(mails.exists())

                # check reply using references
                # TDE TODO: update tooling
                outgoing_message_ids = [
                    outgoing["message_id"] for outgoing in self._mails
                ]
                self.assertEqual(
                    len(set(outgoing_message_ids)),
                    len(self.test_records),
                    "All message IDs should be different",
                )
                for record in self.test_records:
                    outgoing = self._find_sent_email(
                        self.user_employee.email_formatted, [record.email_from]
                    )
                    # for some reason, provider rewrites message_id, then customer replies
                    outgoing["message_id"] = (
                        f"<ILikeToRewriteMessageIDFor{record.id}-{record._name}@zboing>"
                    )
                    extra = f"In-Reply-To:{outgoing['message_id']}\nReferences:{outgoing['message_id']} {outgoing['references']}\n"
                    with RecordCapturer(self.env["mail.message"]) as capture_messages:
                        gateway_record = self.format_and_process(
                            MAIL_TEMPLATE,
                            outgoing["email_to"][0],
                            outgoing["reply_to"],
                            extra=extra,
                            subject=f"Re: {outgoing['subject']} - from {outgoing['email_to'][0]} ({reply_to_mode} {auto_delete_keep_log})",
                            debug_log=False,
                        )
                    new_message = capture_messages.records
                    # as outgoing mail is unlinked with its mail.message -> cannot find parent -> bounce
                    if reply_to_mode == "update" and not auto_delete_keep_log:
                        self.assertFalse(new_message)
                        self.assertFalse(gateway_record)
                        continue
                    self.assertTrue(new_message)
                    if reply_to_mode == "update":
                        self.assertFalse(
                            gateway_record,
                            "No record created based on subject, as it replies to the thread",
                        )
                        self.assertMessageFields(
                            new_message,
                            {
                                "email_from": record.email_from,
                                "model": record._name,
                                "res_id": record.id,
                            },
                        )
                    else:
                        self.assertNotEqual(gateway_record, record)
                        self.assertMessageFields(
                            new_message,
                            {
                                "email_from": record.email_from,
                                "model": gateway_record._name,
                                "res_id": gateway_record.id,
                            },
                        )

    def test_routing_with_out_of_office(self):
        """Test email exchanges with out-of-office messages activated, to check
        gateway support"""
        self.user_admin.notification_type = "email"

        with self.mock_datetime_and_now(datetime(2025, 6, 17, 14, 15, 59)):
            self._setup_out_of_office(self.user_employee)

        with self.mock_mail_gateway(), self.mock_mail_app():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                self.alias.alias_full_name,
                subject="Gateway Creation",
            )
        record.with_user(self.user_admin).write(
            {
                "user_id": self.user_employee,
            }
        )
        self.assertEqual(len(self._new_msgs), 1)
        initial_msg = self._new_msgs
        self.assertFalse(initial_msg.author_id)
        self.assertEqual(initial_msg.email_from, self.email_from)

        # intenal user email reply
        with self.mock_datetime_and_now(datetime(2025, 6, 17, 14, 16, 00)):
            with self.mock_mail_gateway(), self.mock_mail_app():
                self.format_and_process(
                    MAIL_TEMPLATE_EXTRA_HTML,
                    self.user_admin.email_formatted,
                    self.alias.alias_full_name,
                    extra=f"In-Reply-To:{initial_msg.message_id}\nReferences:{initial_msg.message_id}\n",
                    extra_html="Admin reply",
                    subject="Admin reply",
                )
        self.assertEqual(len(self._new_msgs), 2, "Reply + OOO message")
        ooo_message = self._new_msgs[1]
        self.assertMailNotifications(
            ooo_message,
            [
                {
                    "content": "<p>Le numéro que vous avez composé n'est plus attribué.</p>",
                    "email_values": {
                        "subject": "Auto: Admin reply",
                    },
                    "message_type": "out_of_office",
                    "message_values": {
                        "author_id": self.partner_employee,
                        "email_from": self.partner_employee.email_formatted,
                        "model": record._name,
                        "partner_ids": self.partner_admin,
                        "notified_partner_ids": self.partner_admin,
                        "res_id": record.id,
                        "subject": "Auto: Admin reply",
                    },
                    "notif": [
                        {"partner": self.partner_admin, "type": "email"},
                    ],
                    "subtype": "mail.mt_comment",
                }
            ],
        )

        # customer reply
        with self.mock_datetime_and_now(datetime(2025, 6, 17, 14, 16, 00)):
            with self.mock_mail_gateway(), self.mock_mail_app():
                self.format_and_process(
                    MAIL_TEMPLATE_EXTRA_HTML,
                    self.email_from,
                    self.alias.alias_full_name,
                    extra=f"In-Reply-To:{initial_msg.message_id}\nReferences:{initial_msg.message_id}\n",
                    extra_html="Customer reply",
                    subject="Customer reply",
                )
        self.assertEqual(len(self._new_msgs), 2, "Reply + OOO message")
        ooo_message = self._new_msgs[1]
        self.assertMailNotifications(
            ooo_message,
            [
                {
                    "content": "<p>Le numéro que vous avez composé n'est plus attribué.</p>",
                    "email_values": {
                        "subject": "Auto: Customer reply",
                    },
                    "message_type": "out_of_office",
                    "message_values": {
                        "author_id": self.partner_employee,
                        "email_from": self.partner_employee.email_formatted,
                        "model": record._name,
                        "outgoing_email_to": self.email_from,
                        "partner_ids": self.env["res.partner"],
                        "notified_partner_ids": self.env["res.partner"],
                        "res_id": record.id,
                        "subject": "Auto: Customer reply",
                    },
                    "notif": [
                        {
                            "email_to": [email_normalize(self.email_from)],
                            "type": "email",
                        },
                    ],
                    "subtype": "mail.mt_comment",
                }
            ],
        )


@tagged("mail_gateway", "mail_thread")
class TestMailThreadCC(MailCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.email_from = "Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>"
        cls.alias = cls.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain_id": cls.mail_alias_domain.id,
                "alias_model_id": cls.env["ir.model"]._get("mail.test.cc").id,
                "alias_name": "cc_record",
            }
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_cc_new(self):
        record = self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"cc_record@{self.alias_domain}",
            cc="cc1@example.com, cc2@example.com",
            target_model="mail.test.cc",
        )
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(sorted(cc), ["cc1@example.com", "cc2@example.com"])

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_cc_update_with_old(self):
        record = self.env["mail.test.cc"].create(
            {"email_cc": "cc1 <cc1@example.com>, cc2@example.com"}
        )
        self.alias.write({"alias_force_thread_id": record.id})

        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"cc_record@{self.alias_domain}",
            cc="cc2 <cc2@example.com>, cc3@example.com",
            target_model="mail.test.cc",
        )
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(
            sorted(cc),
            ['"cc1" <cc1@example.com>', "cc2@example.com", "cc3@example.com"],
            "new cc should have been added on record (unique)",
        )

    @mute_logger(
        "odoo.addons.mail.models.mixin_mail_thread",
        "odoo.addons.mail.models.mixin_mail_gateway",
        "odoo.addons.mail.tools.mime",
    )
    def test_message_cc_update_no_old(self):
        record = self.env["mail.test.cc"].create({})
        self.alias.write({"alias_force_thread_id": record.id})

        self.format_and_process(
            MAIL_TEMPLATE,
            self.email_from,
            f"cc_record@{self.alias_domain}",
            cc="cc2 <cc2@example.com>, cc3@example.com",
            target_model="mail.test.cc",
        )
        cc = email_split_and_format(record.email_cc)
        self.assertEqual(
            sorted(cc),
            ['"cc2" <cc2@example.com>', "cc3@example.com"],
            "new cc should have been added on record (unique)",
        )


class TestMailgatewayDedup(MailGatewayCommon):
    """C1a — duplicate Message-Id dedup (upstream d1e8df4a advisory lock).

    Processing the same Message-Id twice must yield a single record: the
    second processing detects the existing mail.message and bails out.
    """

    def test_message_process_duplicate_message_id(self):
        mail = self.format(
            MAIL_TEMPLATE,
            to=f"groups@{self.alias_domain}",
            subject="C1a Dedup",
            email_from=self.email_from,
            msg_id="<c1a-duplicate@test.example.com>",
        )
        thread = self.env["mixin.mail.thread"].sudo()
        thread.message_process(None, mail)
        second = thread.message_process(None, mail)

        records = self.env["mail.test.gateway"].search([("name", "=", "C1a Dedup")])
        self.assertEqual(
            len(records),
            1,
            "a duplicate Message-Id must not create a second record",
        )
        self.assertFalse(
            second,
            "processing a duplicate Message-Id must return False",
        )
        self.assertEqual(
            self.env["mail.message"].search_count(
                [("message_id", "=", "<c1a-duplicate@test.example.com>")]
            ),
            1,
            "only one mail.message should carry the duplicated Message-Id",
        )


@tagged("mail_gateway")
class TestMailGatewayRegressions(MailGatewayCommon):
    """Three defects the suite could not see, each reached through a whole email."""

    def test_a_pinged_parent_author_stays_in_partner_ids(self):
        """`partner_ids` is the recipient set the message records, and a plain
        list of ids on an m2m is `Command.SET`. Recording the incoming email's
        own recipients afterwards therefore used to drop whoever `message_post`
        had just been given -- the parent's author, pinged on a reply to a note
        -- leaving a `mail.notification` row for a partner the message denied
        ever addressing.
        """
        author = self.env["res.partner"].create(
            {"name": "Note Author", "email": "note.author@test.example.com"}
        )
        cc_partner = self.env["res.partner"].create(
            {"name": "Cc Partner", "email": "cc.partner@test.example.com"}
        )
        note = self.test_record.message_post(
            author_id=author.id,
            body="internal note",
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_note").id,
        )

        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"{self.alias.alias_full_name}, {cc_partner.email}",
                extra=f"In-Reply-To:\r\n\t{note.message_id}\r\n",
                msg_id="<ping-parent-author@test.example.com>",
                subject="Re: internal note",
                target_model="mail.test.gateway",
            )

        reply = self.test_record.message_ids[0]
        self.assertEqual(reply.parent_id, note, "the note is the anchor")
        self.assertIn(
            author,
            reply.notification_ids.res_partner_id,
            "the parent's author is pinged on a reply to a note",
        )
        self.assertIn(
            author,
            reply.partner_ids,
            "and a partner the gateway notified must stay a recipient of the "
            "message: a bare id list is Command.SET and used to drop them",
        )
        self.assertIn(
            cc_partner,
            reply.partner_ids,
            "the incoming email's own recognized recipients are still recorded",
        )

    def test_a_reply_is_not_refused_by_an_alias_it_never_wrote_to(self):
        """A reply matching no alias used to be judged by an arbitrary alias of
        the model -- the lowest id -- so one `alias_contact='followers'` alias
        anywhere on the model bounced every reply from a non-follower, including
        replies addressed nowhere near it.
        """
        self.alias.alias_contact = "followers"
        restricted = self.env["mail.alias"].create(
            {
                "alias_contact": "followers",
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_model_id": self.mail_test_gateway_model.id,
                "alias_name": "restricted-elsewhere",
            }
        )
        self.assertNotIn(
            "everyone",
            (self.alias + restricted).mapped("alias_contact"),
            "the model must carry no open alias, or the old code short-circuited",
        )
        stranger = '"Stranger" <stranger@test.example.com>'
        self.assertNotIn(
            email_normalize(stranger),
            self.test_record.message_partner_ids.mapped("email_normalized"),
            "the sender is not a follower of the record they are replying to",
        )

        before = len(self.test_record.message_ids)
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                stranger,
                "not.an.alias@test.example.com",
                extra=f"In-Reply-To:\r\n\t{self.fake_email.message_id}\r\n",
                msg_id="<reply-to-no-alias@test.example.com>",
                subject="Re: Generic Message",
                target_model="mail.test.gateway",
            )

        self.test_record.invalidate_recordset()
        self.assertEqual(
            len(self.test_record.message_ids),
            before + 1,
            "the reply belongs on the thread it answers; an alias the mail was "
            "never addressed to does not get to refuse it",
        )
        self.assertFalse(
            self._new_mails.filtered(lambda mail: "MAILER-DAEMON" in mail.email_from),
            "and nothing is bounced back to the sender",
        )

    def test_a_bounce_known_only_by_partner_still_marks_its_notification(self):
        """`_routing_bounce_mark_notifications` builds its domain from the
        partner *or* the email, but the caller only ever reached it when an
        email had been parsed out. A DSN with no usable `Final-Recipient` names
        its victim through the bounced message's single notification instead --
        and if that partner has no email, the whole bounce used to be dropped.
        """
        victim = self.env["res.partner"].create(
            {"name": "Victim", "email": "victim@remote.example.com"}
        )
        with self.mock_mail_gateway():
            bounced = self.test_record.message_post(
                body="outgoing",
                message_type="comment",
                partner_ids=victim.ids,
                subtype_id=self.env.ref("mail.mt_comment").id,
            )
        self.env.flush_all()
        notification = (
            self.env["mail.notification"]
            .sudo()
            .search([("mail_message_id", "=", bounced.id)])
        )
        self.assertEqual(len(notification), 1, "one notification names the victim")
        self.assertFalse(
            notification.mail_email_address,
            "the address used is not recorded on the notification either, so the "
            "partner is the only handle the bounce has",
        )
        # the address is cleaned off the partner between the send and the bounce:
        # a merge, an erasure request, a corrected typo
        victim.email = False
        self.env.flush_all()
        self.assertFalse(victim.email_normalized)

        boundary = "==BOUNDARY=="
        bounce_mail = "\r\n".join(
            [
                "Return-Path: <>",
                "From: MAILER-DAEMON <mailer-daemon@test.example.com>",
                f"To: {self.alias_bounce}@{self.alias_domain}",
                "Subject: Undelivered Mail Returned to Sender",
                "Message-Id: <partner-only-bounce@test.example.com>",
                "MIME-Version: 1.0",
                f'Content-Type: multipart/report; report-type=delivery-status; boundary="{boundary}"',
                "",
                f"--{boundary}",
                "Content-Type: text/plain; charset=utf-8",
                "",
                "Delivery failed.",
                "",
                f"--{boundary}",
                "Content-Type: message/delivery-status",
                "",
                "Reporting-MTA: dns; test.example.com",
                "",
                f"--{boundary}",
                "Content-Type: message/rfc822",
                "",
                f"Message-Id: {bounced.message_id}",
                "Subject: Generic Message",
                "",
                "original body",
                f"--{boundary}--",
                "",
            ]
        )
        with self.mock_mail_gateway():
            self.env["mixin.mail.thread"].message_process(None, bounce_mail)

        notification.invalidate_recordset()
        self.assertEqual(
            notification.notification_status,
            "bounce",
            "the bounce named its victim through the notification, not through "
            "a Final-Recipient; a partner with no email is still a partner",
        )
        self.assertEqual(notification.failure_type, "mail_bounce")

    def test_a_reply_is_still_judged_by_the_record_s_own_alias(self):
        """The other half of the same fix, and the reason it is a narrowing
        rather than a deletion.

        Routing a reply on References alone would let anyone who learns a
        Message-Id post into a followers-only thread by forging `In-Reply-To`.
        The record's *own* alias still governs that -- what was removed is only
        the fallback to an arbitrary alias of the model, which spoke for a
        record the mail had nothing to do with.
        """
        group = self.env["mail.test.gateway.groups"].create(
            {"alias_name": "own-alias-probe", "name": "Owns its alias"}
        )
        group.alias_id.alias_contact = "followers"
        seed = group.message_post(
            body="seed",
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
        )
        outsider = self.env["res.partner"].create(
            {"name": "Outsider", "email": "outsider@remote.example.com"}
        )
        self.assertNotIn(outsider, group.message_partner_ids)

        def reply(msg_id):
            before = len(group.message_ids)
            with self.mock_mail_gateway():
                self.format_and_process(
                    MAIL_TEMPLATE,
                    '"Outsider" <outsider@remote.example.com>',
                    "somewhere-else@test.mycompany.com",
                    extra=f"In-Reply-To:\r\n\t{seed.message_id}\r\n",
                    msg_id=msg_id,
                    subject=f"Re: seed {msg_id}",
                    target_model="mail.test.gateway.groups",
                )
            group.invalidate_recordset()
            return len(group.message_ids) > before

        self.assertFalse(
            reply("<own-alias-refuses@test.example.com>"),
            "the record's own followers-only alias refuses a stranger's reply",
        )
        group.message_subscribe(partner_ids=outsider.ids)
        self.assertTrue(
            reply("<own-alias-accepts@test.example.com>"),
            "and accepts the same reply once they follow the record",
        )

    def test_a_reply_to_a_vanished_document_is_judged_by_the_alias_owner(self):
        """`_routing_check_target` resets `thread_id` to None on a missing
        document but leaves `record_set` a truthy browse of the id that is gone.
        Two different guards, and collapsing them is silent: the alias check then
        runs against the empty model instead of the alias' owner, which for
        `alias_contact='followers'` is `config_follower_no_record` -- a refusal
        *and* `_alias_mark_invalid`, disabling a correctly configured alias.
        """
        owner = self.env["mail.test.gateway"].create({"name": "Owner doc"})
        follower = self.env["res.partner"].create(
            {"name": "Follower", "email": "follower@remote.example.com"}
        )
        owner.message_subscribe(partner_ids=follower.ids)
        alias = self.env["mail.alias"].create(
            {
                "alias_contact": "followers",
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_model_id": self.mail_test_gateway_model.id,
                "alias_name": "owner-answers",
                "alias_parent_model_id": self.mail_test_gateway_model.id,
                "alias_parent_thread_id": owner.id,
            }
        )
        vanished = self.env["mail.test.gateway"].browse(
            max(self.env["mail.test.gateway"].search([]).ids) + 5000
        )
        self.assertTrue(vanished, "a browse of a missing id is still truthy")
        self.assertFalse(vanished.exists(), "but the document is gone")

        message = email.message_from_string(
            "From: Follower <follower@remote.example.com>\r\n"
            "To: x@y.example.com\r\nSubject: s\r\n"
            "Message-Id: <vanished-doc@test.example.com>\r\n\r\nbody\r\n",
            policy=email.policy.SMTP,
        )
        message_dict = {
            "author_id": follower.id,
            "email_from": "follower@remote.example.com",
            "message_id": "<vanished-doc@test.example.com>",
            "to": "x@y.example.com",
        }
        route = Route("mail.test.gateway", None, None, self.env.uid, alias)

        with self.mock_mail_gateway():
            accepted = self.env["mixin.mail.gateway"]._routing_check_alias_accepts(
                message, message_dict, route, vanished, None
            )
        self.assertTrue(
            accepted,
            "the alias' owner document answers for the alias, and its follower "
            "is the sender",
        )
        alias.invalidate_recordset()
        self.assertEqual(
            alias.alias_status,
            "not_tested",
            "a correctly configured alias must not be marked invalid because the "
            "document being replied to was deleted",
        )

    def test_one_broken_alias_does_not_discard_the_other_addressees(self):
        """`_routing_check_alias_routes` raised on the first unusable alias, which
        threw away the routes of every *other* alias the mail was addressed to.
        An alias whose target model stopped accepting mail is that alias' problem.
        """
        broken = self.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_model_id": self.mail_test_gateway_model.id,
                "alias_name": "broken",
            }
        )
        # the @api.constrains refuses this target, so reproduce the state a
        # database reaches on its own: an alias that was valid when it was made
        # and whose model later stopped storing documents
        self.env.cr.execute(
            "UPDATE mail_alias SET alias_model_id = %s WHERE id = %s",
            [self.env["ir.model"]._get_id("mixin.mail.thread"), broken.id],
        )
        broken.invalidate_recordset()
        self.assertEqual(broken.alias_model_id.model, "mixin.mail.thread")

        with (
            self.mock_mail_gateway(),
            mute_logger("odoo.addons.mail.models.mixin_mail_gateway"),
        ):
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"{broken.alias_full_name}, {self.alias.alias_full_name}",
                msg_id="<broken-plus-good@test.example.com>",
                subject="Broken and good",
                target_model="mail.test.gateway",
            )
        self.assertTrue(
            record,
            "the usable alias still routes; one broken addressee does not "
            "discard the mail for the others",
        )

    def test_a_mail_addressed_only_to_a_broken_alias_still_raises(self):
        """The other half: swallowing the error when nothing routed would turn a
        misconfiguration into silence."""
        broken = self.env["mail.alias"].create(
            {
                "alias_contact": "everyone",
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_model_id": self.mail_test_gateway_model.id,
                "alias_name": "broken-alone",
            }
        )
        self.env.cr.execute(
            "UPDATE mail_alias SET alias_model_id = %s WHERE id = %s",
            [self.env["ir.model"]._get_id("mixin.mail.thread"), broken.id],
        )
        broken.invalidate_recordset()

        with (
            self.mock_mail_gateway(),
            mute_logger("odoo.addons.mail.models.mixin_mail_gateway"),
            self.assertRaises(ValueError),
        ):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                broken.alias_full_name,
                msg_id="<broken-alone@test.example.com>",
                subject="Broken alone",
                target_model="mail.test.gateway",
            )

    def test_a_database_with_no_sender_at_all_declines_to_bounce(self):
        """`formataddr(("MAILER-DAEMON", False))` raises `AttributeError`, so a
        database configuring no bounce address at all crashed the gateway instead
        of bouncing. There is no address to send from; the answer is to send
        nothing and say so, not to die inside `email.utils`.
        """
        self.env["res.company"].sudo().search([]).write({"alias_domain_id": False})
        self.env["mail.alias.domain"].sudo().search([]).write({"default_from": False})
        self.env.user.partner_id.email = False
        self.env.flush_all()

        message = email.message_from_string(
            "From: someone@remote.example.com\r\nTo: nobody@nowhere.example.com\r\n"
            "Subject: s\r\nMessage-Id: <no-sender@test.example.com>\r\n\r\nbody\r\n",
            policy=email.policy.SMTP,
        )
        gateway = self.env["mixin.mail.thread"]
        self.assertFalse(
            gateway._routing_get_bounce_from(message),
            "nothing is configured, so there is no bounce sender",
        )
        with self.mock_mail_gateway():
            gateway._routing_create_bounce_email(
                "someone@remote.example.com", Markup("<p>bounced</p>"), message
            )
        self.assertFalse(self._new_mails, "and no bounce is sent")

    def test_an_exactly_addressed_alias_suppresses_the_same_local_part_elsewhere(self):
        """`_routing_filtered_local_aliases` is a fork-only rule and nothing tested it.

        `alias_incoming_local` makes an alias answer on its local part whatever
        the domain, which is deliberate. But when a mail names one alias by its
        full address, an alias sharing only its local part on another domain was
        never a recipient of that mail -- and routing both creates a record on
        each model for a message addressed to one of them.
        """
        self.alias_c2.alias_incoming_local = True
        self.assertEqual(
            self.alias.alias_name,
            self.alias_c2.alias_name,
            "the fixture's two aliases share a local part across two domains",
        )
        self.assertNotEqual(self.alias.alias_model_id, self.alias_c2.alias_model_id)

        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                self.alias.alias_full_name,
                msg_id="<local-part-collision@test.example.com>",
                subject="Local part collision",
                target_model="mail.test.gateway",
            )
        self.assertTrue(record, "the exactly addressed alias routes")
        self.assertEqual(
            self.env["mail.test.gateway.company"].search_count(
                [("name", "=", "Local part collision")]
            ),
            0,
            "the alias that merely shares the local part on another domain was "
            "not addressed and must not get a record too",
        )

    def test_a_local_part_alias_still_answers_for_a_domain_we_do_not_own(self):
        """The other half, so the rule above cannot be widened into a ban.

        With nothing addressed by full name, no local part is claimed, and
        `alias_incoming_local` does what it exists for.
        """
        self.alias_c2.alias_incoming_local = True
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"{self.alias_c2.alias_name}@unowned.example.com",
                msg_id="<local-part-elsewhere@test.example.com>",
                subject="Local part elsewhere",
                target_model="mail.test.gateway.company",
            )
        self.assertEqual(
            self.env["mail.test.gateway.company"].search_count(
                [("name", "=", "Local part elsewhere")]
            ),
            1,
            "no alias was addressed by full name, so the local-part alias answers",
        )

    def test_the_creation_threshold_fires_exactly_at_the_threshold(self):
        """The counter short-circuits at `limit=threshold`, which is only correct
        because `search_count(limit=N)` returns `min(count, N)`. Get that backwards
        and loop detection stops firing -- silently, since nothing else asserts on
        the count.
        """
        sender = "loop.boundary@test.example.com"
        self.env["mail.test.gateway"].create(
            [{"name": f"Loop {index}", "email_from": sender} for index in range(3)]
        )
        limit = self.env.cr.now() - timedelta(minutes=120)
        model = self.env["mail.test.gateway"]
        for threshold, expected in ((2, True), (3, True), (4, False)):
            with self.subTest(threshold=threshold):
                self.assertEqual(
                    model._has_loop_sender_created_too_many(
                        [False], sender, limit, threshold
                    ),
                    expected,
                    "three records from this sender: a loop at a threshold of "
                    "three, not at four",
                )

    def test_the_creation_counter_escapes_like_wildcards_in_the_address(self):
        """`_` is a single-character wildcard to LIKE. An address carrying one
        would otherwise count records belonging to addresses it never matched,
        and trip loop detection on somebody else's mail.

        On `mail.test.ticket` deliberately, NOT on the gateway fixture: the
        blacklist mixin overrides the domain with an exact match on
        `email_normalized` and never calls super, so a blacklist model exercises
        no LIKE at all and would pass this whatever the base did. The escaping
        being asserted here is only reachable through a plain thread model.
        """
        blacklist = self.env.registry["mixin.mail.thread.blacklist"]
        self.assertNotIsInstance(
            self.env["mail.test.ticket"],
            blacklist,
            "this model must reach the gateway's own domain, not the override",
        )
        self.assertIsInstance(
            self.env["mail.test.gateway"],
            blacklist,
            "and the gateway fixture must not be used here, because it does not",
        )

        with_underscore = "a_b@test.example.com"
        lookalike = "axb@test.example.com"
        self.env["mail.test.ticket"].create(
            [
                {"name": "Underscore", "email_from": with_underscore},
                {"name": "Lookalike", "email_from": lookalike},
            ]
        )
        limit = self.env.cr.now() - timedelta(minutes=120)
        model = self.env["mail.test.ticket"]
        self.assertTrue(
            model._has_loop_sender_created_too_many([False], with_underscore, limit, 1),
            "it still finds its own record",
        )
        self.assertFalse(
            model._has_loop_sender_created_too_many([False], with_underscore, limit, 2),
            "but only its own -- `a_b@` must not also match `axb@`",
        )


@tagged("mail_gateway")
class TestMailGatewayNonThreadTarget(MailGatewayCommon):
    """An alias owner that implements the two gateway hooks takes mail whether
    or not it is a thread: the alias constraint and the router ask one question."""

    def test_an_alias_owner_without_a_thread_still_receives_mail(self):
        owner = self.env["mail.test.gateway.nothread"].create(
            {
                "name": "The list",
                "alias_name": "list",
                "alias_domain_id": self.mail_alias_domain.id,
                "alias_contact": "everyone",
            }
        )
        self.assertEqual(owner.alias_id.alias_force_thread_id, owner.id)
        self.assertTrue(self.env["mail.alias"]._alias_model_accepts_mail(owner))
        self.assertEqual(
            self.env["mixin.mail.thread"]._routing_get_alias_model(owner._name)._name,
            "mixin.mail.thread",
            "no routing hook of its own, so the mixin's checks apply",
        )
        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"list@{self.alias_domain}",
                subject="To the list",
                target_model=owner._name,
            )
        self.assertEqual(owner.received_subjects, "To the list")


@tagged("mail_gateway")
class TestMailGatewayParsedMessageContract(MailGatewayCommon):
    """The parsed message is a contract: what `message_parse` promises, every
    route check downstream may index without a `.get`."""

    def _mails_on(self, record, count, email_from=False):
        self.env["mail.message"].sudo().create(
            [
                {
                    "author_id": False,
                    "email_from": email_from,
                    "message_type": "email",
                    "model": record._name,
                    "res_id": record.id,
                    "subtype_id": self.env.ref("mail.mt_comment").id,
                }
                for _ in range(count)
            ]
        )

    def test_stripped_attachments_leave_the_key_in_place(self):
        """`account.move._routing_check_route` indexes `message_dict["attachments"]`;
        stripping used to pop the key and the invoice guard died on a KeyError."""
        seen = {}

        def message_route(gateway, message, message_dict, *args, **kwargs):
            seen.update(message_dict)
            return []

        with patch.object(
            self.registry["mixin.mail.thread"],
            "message_route",
            autospec=True,
            side_effect=message_route,
        ):
            self.env["mixin.mail.thread"].message_process(
                "mail.test.gateway",
                test_mail_data.MAIL_MULTIPART_MIXED,
                strip_attachments=True,
            )
        self.assertIn("attachments", seen)
        self.assertEqual(seen["attachments"], [])

    def test_recipients_are_normalised_once_by_the_parser(self):
        message = self.from_string(
            self.format(
                MAIL_TEMPLATE,
                to='"Groups" <GROUPS@Test.MyCompany.com>, Other@Example.COM',
                cc="Copied <CC@Example.com>",
                email_from=self.email_from,
            )
        )
        message_dict = self.env["mixin.mail.thread"].message_parse(message)
        self.assertEqual(
            message_dict["to_normalized"],
            ["groups@test.mycompany.com", "other@example.com"],
        )
        self.assertEqual(
            message_dict["recipients_normalized"],
            ["groups@test.mycompany.com", "other@example.com", "cc@example.com"],
        )
        self.assertTrue(
            self.env["mixin.mail.thread"]._is_write_to_catchall(
                {"to_normalized": [f"{self.alias_catchall}@{self.alias_domain}"]}
            )
        )

    def test_in_reply_to_is_one_unfolded_message_id(self):
        """A folded `In-Reply-To` carrying a comment is still the parent's id, so
        the reply lands on the thread instead of creating a new document."""
        message = self.from_string(
            self.format(
                MAIL_TEMPLATE,
                to="somewhere-else@test.mycompany.com",
                email_from=self.partner_1.email_formatted,
                extra=f"In-Reply-To: (their client)\r\n\t{self.fake_email.message_id}\r\n",
            )
        )
        message_dict = self.env["mixin.mail.thread"].message_parse(message)
        self.assertEqual(message_dict["in_reply_to"], self.fake_email.message_id)

        with self.mock_mail_gateway():
            self.format_and_process(
                MAIL_TEMPLATE,
                self.partner_1.email_formatted,
                "somewhere-else@test.mycompany.com",
                extra=f"In-Reply-To: (their client)\r\n\t{self.fake_email.message_id}\r\n",
                subject="Re: folded reply",
            )
        reply = self.test_record.message_ids.filtered(
            lambda message: message.subject == "Re: folded reply"
        )
        self.assertEqual(len(reply), 1, "the reply reached the thread it names")
        self.assertEqual(reply.parent_id, self.fake_email)

    def test_a_null_return_path_is_not_bounced_to(self):
        """RFC 5321: `Return-Path: <>` asks for no delivery status notification.
        A bounce to it used to be created and stick in exception."""
        self.alias.write({"alias_contact": "partners"})
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                '"Nobody Known" <nobody@remote.example.com>',
                f"groups@{self.alias_domain}",
                return_path="<>",
                subject="Null reverse path",
            )
        self.assertFalse(record, "the partners-only alias still refuses the mail")
        self.assertNotSentEmail()

        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                '"Nobody Known" <nobody@remote.example.com>',
                f"groups@{self.alias_domain}",
                return_path="<bounces+tag@remote.example.com>",
                subject="Real reverse path",
            )
        self.assertFalse(record)
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["bounces+tag@remote.example.com"],
            subject="Re: Real reverse path",
        )

    def test_loop_replies_never_count_author_less_messages_for_an_unparsable_from(self):
        """`email_from in [raw, False]` became `IS NULL` and counted every message
        posted without a sender as if this sender had posted it."""
        record = self.env["mail.test.gateway"].create({"name": "Quiet"})
        self._mails_on(record, 6, email_from=False)
        limit = self.env.cr.now() - timedelta(minutes=120)
        self.assertFalse(
            record._has_loop_sender_replied_too_often(
                record.ids, "not an address", False, False, limit, 5
            )
        )
        self._mails_on(record, 6, email_from="not an address")
        self.assertTrue(
            record._has_loop_sender_replied_too_often(
                record.ids, "not an address", False, False, limit, 5
            ),
            "the raw address alone still identifies the sender",
        )


@tagged("mail_gateway", "multi_company")
class TestMailGatewayBounceCompany(MailGatewayCommon):
    """A bounce answers for the company that was written to, not for whoever
    happens to be `env.company` when the gateway runs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("mail.gateway.loop.minutes", 30)
        cls.env["ir.config_parameter"].sudo().set_param(
            "mail.gateway.loop.threshold", 1
        )

    def test_the_alias_policy_bounce_is_sent_from_the_alias_company(self):
        self.alias_c2.write({"alias_contact": "partners"})
        self.assertNotEqual(self.env.company, self.company_2)
        self.assertNotEqual(
            self.mail_alias_domain.bounce_email, self.mail_alias_domain_c2.bounce_email
        )
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                '"Nobody Known" <nobody@remote.example.com>',
                f"groups@{self.mail_alias_domain_c2.name}",
                subject="Company two policy",
                target_model="mail.test.gateway.company",
            )
        self.assertFalse(record)
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.mail_alias_domain_c2.bounce_email}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Company two policy",
        )

    @mute_logger("odoo.addons.mail.models.mixin_mail_gateway")
    def test_the_loop_bounce_is_sent_from_the_alias_company(self):
        sender = '"Chatty" <chatty@remote.example.com>'
        with self.mock_mail_gateway():
            first = self.format_and_process(
                MAIL_TEMPLATE,
                sender,
                f"groups@{self.mail_alias_domain_c2.name}",
                subject="Loop one",
                target_model="mail.test.gateway.company",
            )
        self.assertTrue(first)
        self.assertEqual(first.company_id, self.company_2)
        with self.mock_mail_gateway():
            second = self.format_and_process(
                MAIL_TEMPLATE,
                sender,
                f"groups@{self.mail_alias_domain_c2.name}",
                subject="Loop two",
                target_model="mail.test.gateway.company",
            )
        self.assertFalse(second, "the threshold of one refuses the second mail")
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.mail_alias_domain_c2.bounce_email}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Loop two",
        )


@tagged("mail_gateway")
class TestMailGatewayRouteVerdicts(MailGatewayCommon):
    @mute_logger("odoo.addons.mail.models.mixin_mail_gateway")
    def test_unparsable_alias_defaults_are_a_configuration_error(self):
        """`_prepare_alias_defaults` ran outside the per-alias `try`, so a stored
        value the constraint never saw crashed routing for every addressee
        instead of bouncing the one broken alias."""
        self.env.cr.execute(
            "UPDATE mail_alias SET alias_defaults = %s WHERE id = %s",
            ["{'custom_field': ", self.alias.id],
        )
        self.alias.invalidate_recordset()
        self.assertEqual(self.alias.alias_status, "not_tested")
        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Broken defaults",
            )
        self.assertFalse(record)
        self.assertEqual(self.alias.alias_status, "invalid")
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
            subject="Re: Broken defaults",
        )

    @mute_logger("odoo.addons.mail.models.mixin_mail_gateway")
    def test_a_refusing_fallback_model_is_consulted_and_obeyed(self):
        """A fetchmail server with `object_id` set routes through the fallback,
        which used to call the mixin's check and skip the target model's own
        (`account.move`'s attachment guard among them)."""
        with (
            patch.object(
                self.registry["mail.test.gateway"],
                "_routing_check_route",
                autospec=True,
                return_value=RouteVerdict.REFUSED,
            ) as check,
            self.mock_mail_gateway(),
        ):
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                "nobody-owns-this@remote.example.com",
                model="mail.test.gateway",
                subject="Refused fallback",
            )
        check.assert_called_once()
        self.assertFalse(record, "a refusal is obeyed, not turned into a crash")

    @mute_logger("odoo.addons.mail.models.mixin_mail_gateway")
    def test_a_check_route_answering_off_contract_is_a_type_error(self):
        with (
            patch.object(
                self.registry["mail.test.gateway"],
                "_routing_check_route",
                autospec=True,
                return_value=(),
            ),
            self.assertRaises(TypeError),
        ):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.email_from,
                f"groups@{self.alias_domain}",
                subject="Off contract",
            )

    @mute_logger("odoo.addons.mail.models.mixin_mail_gateway")
    def test_bounce_counters_reset_only_once_a_route_has_posted(self):
        """The reset ran before any route was accepted, so an unroutable mail
        with a spoofed From cleared the counters of the address it borrowed."""
        self.test_record.write({"message_bounce": 3})
        with self.mock_mail_gateway(), self.assertRaises(ValueError):
            self.format_and_process(
                MAIL_TEMPLATE,
                self.test_record.email_from,
                "nobody-owns-this@test.mycompany.com",
                subject="Unroutable",
            )
        self.assertEqual(self.test_record.message_bounce, 3)

        with self.mock_mail_gateway():
            record = self.format_and_process(
                MAIL_TEMPLATE,
                self.test_record.email_from,
                f"groups@{self.alias_domain}",
                subject="Delivered",
            )
        self.assertTrue(record)
        self.assertEqual(self.test_record.message_bounce, 0)

    def test_an_inbound_email_searches_the_aliases_once(self):
        """A reply searched twice (other-model aliases on To, then reply aliases on
        To+Cc) and a new mail once more; every step now filters one candidate set."""
        MailAlias = self.registry["mail.alias"]
        cases = (
            ("new", {}),
            ("reply", {"extra": f"In-Reply-To: {self.fake_email.message_id}"}),
        )
        for label, extra in cases:
            with (
                self.subTest(label=label),
                patch.object(
                    MailAlias, "search", autospec=True, side_effect=MailAlias.search
                ) as search,
                self.mock_mail_gateway(),
            ):
                self.format_and_process(
                    MAIL_TEMPLATE,
                    self.email_from,
                    f"groups@{self.alias_domain}",
                    subject=label,
                    msg_id=f"<{label}@iron.sky>",
                    **extra,
                )
            self.assertEqual(search.call_count, 1)

    def test_a_reply_to_a_child_document_is_judged_by_its_parent_s_alias(self):
        """Tasks and tickets own no alias; their project or team does. A reply
        routed by References alone used to bypass that alias' contact policy."""
        container = self.env["mail.test.container.mc"].create(
            {"alias_contact": "followers", "alias_name": "governing", "name": "Gov"}
        )
        ticket = self.env["mail.test.ticket.mc"].create(
            {"container_id": container.id, "name": "Governed"}
        )
        self.assertEqual(ticket._mail_get_governing_alias(), container.alias_id)
        seed = ticket.message_post(
            body="seed",
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
        )
        outsider = self.env["res.partner"].create(
            {"name": "Outsider", "email": "outsider@remote.example.com"}
        )

        def reply(msg_id):
            before = len(ticket.message_ids)
            with self.mock_mail_gateway():
                self.format_and_process(
                    MAIL_TEMPLATE,
                    outsider.email_formatted,
                    "somewhere-else@test.mycompany.com",
                    extra=f"In-Reply-To:\r\n\t{seed.message_id}\r\n",
                    msg_id=msg_id,
                    subject=f"Re: seed {msg_id}",
                    target_model="mail.test.ticket.mc",
                )
            ticket.invalidate_recordset()
            return len(ticket.message_ids) > before

        self.assertFalse(
            reply("<parent-alias-refuses@test.example.com>"),
            "the parent's followers-only alias refuses a stranger's reply",
        )
        self.assertSentEmail(
            f'"MAILER-DAEMON" <{self.alias_bounce}@{self.alias_domain}>',
            ["whatever-2a840@postmaster.twitter.com"],
        )
        ticket.message_subscribe(partner_ids=outsider.ids)
        self.assertTrue(
            reply("<parent-alias-accepts@test.example.com>"),
            "and accepts the same reply once they follow the document",
        )
