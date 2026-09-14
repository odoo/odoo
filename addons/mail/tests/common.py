import base64
import contextlib
import email
import email.policy
import json
import logging
import time
from contextlib import contextmanager
from datetime import UTC, timedelta
from functools import partial
from random import randint
from unittest.mock import MagicMock, Mock, patch
from urllib.parse import parse_qsl, urlencode, urlparse

from freezegun import freeze_time
from lxml import html
from markupsafe import Markup

from odoo import Command, fields, tools
from odoo.tests import RecordCapturer, common, new_test_user
from odoo.tools import mute_logger
from odoo.tools.mail import (
    email_normalize,
    email_split_and_format,
    email_split_and_format_normalize,
    formataddr,
)
from odoo.tools.translate import code_translations

from odoo.addons.bus.models.bus import BusBus, json_dump
from odoo.addons.bus.tests.common import BusCase
from odoo.addons.mail.models import mail_push, mixin_mail_thread
from odoo.addons.mail.models.ir_mail_server import IrMail_Server
from odoo.addons.mail.models.mail_mail import MailMail
from odoo.addons.mail.models.mail_message import MailMessage
from odoo.addons.mail.models.mail_notification import MailNotification
from odoo.addons.mail.models.res_users import ResUsers
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.mail.tools.recipients import prepare_recipient_data

_logger = logging.getLogger(__name__)

mail_new_test_user = partial(
    new_test_user,
    context={
        "mail_create_nolog": True,
        "mail_create_nosubscribe": True,
        "mail_notrack": True,
        "no_reset_password": True,
    },
)


class MockSmtplibCase:
    @contextmanager
    def mock_smtplib_connection(self):
        self.emails = []

        origin = self
        IrMail_Server = type(self.env["ir.mail_server"])

        class TestingSMTPSession:
            def quit(self):
                pass

            def send_message(self, message, smtp_from, smtp_to_list):
                origin.emails.append(
                    {
                        "message": message.as_string(),
                        "msg_cc": message["Cc"],
                        "msg_from": message["From"],
                        "msg_from_fmt": email_split_and_format(message["From"])[0],
                        "msg_to": message["To"],
                        "smtp_from": smtp_from,
                        "smtp_to_list": smtp_to_list,
                        "from_filter": IrMail_Server._read_session_context(
                            self
                        ).from_filter,
                    }
                )

            def set_debuglevel(self, smtp_debug):
                pass

            def ehlo_or_helo_if_needed(self):
                pass

            def login(self, user, password):
                pass

            def starttls(self, keyfile=None, certfile=None, context=None):
                pass

        self.testing_smtp_session = TestingSMTPSession()

        IrMailServer = self.env["ir.mail_server"]
        connect_origin = type(IrMailServer)._connect__
        find_mail_server_origin = type(IrMailServer)._get_mail_server

        def mock_function(func):
            mock = Mock()

            def _call(*args, **kwargs):
                mock(*args[1:], **kwargs)
                return func(*args, **kwargs)

            _call.mock = mock
            return _call

        with (
            patch(
                "smtplib.SMTP_SSL",
                side_effect=lambda *args, **kwargs: self.testing_smtp_session,
            ),
            patch(
                "smtplib.SMTP",
                side_effect=lambda *args, **kwargs: self.testing_smtp_session,
            ),
            patch.object(type(IrMailServer), "_disable_send", lambda _: False),
            patch.object(
                type(IrMailServer), "_connect__", mock_function(connect_origin)
            ) as connect_mocked,
            patch.object(
                type(IrMailServer),
                "_get_mail_server",
                mock_function(find_mail_server_origin),
            ) as find_mail_server_mocked,
        ):
            self.connect_mocked = connect_mocked.mock
            self.find_mail_server_mocked = find_mail_server_mocked.mock
            yield

    def _build_email(self, mail_from, return_path=None, **kwargs):
        headers = {"Return-Path": return_path} if return_path else {}
        headers.update(**kwargs.pop("headers", {}))
        return self.env["ir.mail_server"]._prepare_email__(
            mail_from,
            kwargs.pop("email_to", "dest@example-é.com"),
            kwargs.pop("subject", "subject"),
            kwargs.pop("body", "body"),
            headers=headers,
            **kwargs,
        )

    def _send_email(self, msg, smtp_session):
        IrMailServer = self.env["ir.mail_server"]
        with patch.object(type(IrMailServer), "_disable_send", lambda _: False):
            IrMailServer.send_email(msg, smtp_session=smtp_session)
        return smtp_session.messages.pop()

    def assertSMTPEmailsSent(
        self,
        smtp_from=None,
        smtp_to_list=None,
        message_from=None,
        msg_from=None,
        mail_server=None,
        from_filter=None,
        emails_count=1,
        msg_cc_lst=None,
        msg_to_lst=None,
    ):
        if from_filter is not None and mail_server:
            msg = "Invalid usage: use either from_filter either mail_server"
            raise ValueError(msg)

        if from_filter is None and mail_server is not None:
            from_filter = mail_server.from_filter
        matching_emails = list(
            filter(
                lambda email: (
                    (smtp_from is None or smtp_from == email["smtp_from"])
                    and (smtp_to_list is None or smtp_to_list == email["smtp_to_list"])
                    and (
                        message_from is None
                        or "From: %s" % message_from in email["message"]
                    )
                    and (
                        msg_from is None
                        or (
                            msg_from == email["msg_from"]
                            or msg_from == email["msg_from_fmt"]
                        )
                    )
                    and (from_filter is None or from_filter == email["from_filter"])
                ),
                self.emails,
            )
        )

        debug_info = ""
        matching_emails_count = len(matching_emails)
        if matching_emails_count != emails_count:
            debug_info = "\n".join(
                f"SMTP-From: {email['smtp_from']}, SMTP-To: {email['smtp_to_list']}, "
                f"Msg-From: {email['msg_from']}, Msg-To: {email['msg_to']}, From_filter: {email['from_filter']})"
                for email in self.emails
            )
        self.assertEqual(
            matching_emails_count,
            emails_count,
            msg=f"Incorrect emails sent: {matching_emails_count} found, {emails_count} expected"
            f"\nConditions\nSMTP-From: {smtp_from}, SMTP-To: {smtp_to_list}, Msg-From: {message_from or msg_from}, From_filter: {from_filter}"
            f"\nNot found in\n{debug_info}",
        )
        if msg_to_lst is not None:
            for email in matching_emails:
                self.assertListEqual(
                    sorted(email_split_and_format(email["msg_to"])),
                    sorted(msg_to_lst),
                )
        if msg_cc_lst is not None:
            for email in matching_emails:
                self.assertListEqual(
                    sorted(email_split_and_format(email["msg_cc"])),
                    sorted(msg_cc_lst),
                )

    @classmethod
    def _init_mail_gateway(cls):
        cls.default_from_filter = False
        cls.env["ir.config_parameter"].sudo().set_param(
            "mail.default.from_filter", cls.default_from_filter
        )

    @classmethod
    def _init_mail_servers(cls):
        cls.env["ir.mail_server"].search([]).unlink()

        ir_mail_server_values = {
            "smtp_host": "smtp_host",
            "smtp_encryption": "none",
        }
        cls.mail_servers = cls.env["ir.mail_server"].create(
            [
                {
                    "name": "Domain based server",
                    "from_filter": "test.mycompany.com",
                    "sequence": 0,
                    **ir_mail_server_values,
                },
                {
                    "name": "User specific server",
                    "from_filter": "specific_user@test.mycompany.com",
                    "sequence": 1,
                    **ir_mail_server_values,
                },
                {
                    "name": "Server Notifications",
                    "from_filter": "notifications.test@test.mycompany.com",
                    "sequence": 2,
                    **ir_mail_server_values,
                },
                {
                    "name": "Server No From Filter",
                    "from_filter": False,
                    "sequence": 3,
                    **ir_mail_server_values,
                },
            ]
        )
        (
            cls.mail_server_domain,
            cls.mail_server_user,
            cls.mail_server_notification,
            cls.mail_server_default,
        ) = cls.mail_servers


class MockEmail(common.BaseCase, MockSmtplibCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._mc_enabled = False

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        if isinstance(mock_dt, str):
            mock_dt = fields.Datetime.to_datetime(mock_dt)
        with freeze_all_time(mock_dt):
            yield

    @contextmanager
    def mock_push_to_end_point(self, max_direct_push=5):
        with (
            self._patch_push_to_end_point() as patched_push,
            patch.object(mixin_mail_thread, "MAX_DIRECT_PUSH", max_direct_push),
        ):
            self.push_to_end_point_mocked = patched_push
            yield

    @staticmethod
    @contextmanager
    def _patch_push_to_end_point():
        patched_push = MagicMock(name="push_to_end_point")
        with (
            patch.object(mixin_mail_thread, "push_to_end_point", patched_push),
            patch.object(mail_push, "push_to_end_point", patched_push),
        ):
            yield patched_push

    def _mock_push_to_end_point(self, max_direct_push=5):
        mock = self.mock_push_to_end_point(max_direct_push=max_direct_push)
        mock.__enter__()
        self.addCleanup(lambda: mock.__exit__(None, None, None))

    @contextmanager
    def mock_mail_gateway(self, mail_unlink_sent=False):
        build_email_origin = IrMail_Server._prepare_email__
        send_email_origin = IrMail_Server.send_email
        mail_create_origin = MailMail.create
        mail_private_send_origin = MailMail._send
        mail_unlink_origin = MailMail.unlink
        self.mail_unlink_sent = mail_unlink_sent
        self._init_mail_mock()

        def _ir_mail_server_build_email(
            model, email_from, email_to, subject, body, **kwargs
        ):
            data = {
                "email_from": email_from,
                "email_to": email_to,
                "subject": subject,
                "body": body,
                **kwargs,
            }
            res = build_email_origin(
                model, email_from, email_to, subject, body, **kwargs
            )
            data["EmailMessage"] = res
            self._mails.append(data)
            return res

        def _mail_mail_create(model, *args, **kwargs):
            res = mail_create_origin(model, *args, **kwargs)
            self._new_mails += res.sudo()
            return res

        def _mail_mail_unlink(model, *args, **kwargs):
            if self.mail_unlink_sent:
                return mail_unlink_origin(model, *args, **kwargs)
            return True

        with (
            self.mock_smtplib_connection(),
            patch.object(
                IrMail_Server,
                "_prepare_email__",
                autospec=True,
                wraps=IrMail_Server,
                side_effect=_ir_mail_server_build_email,
            ) as build_email_mocked,
            patch.object(
                IrMail_Server,
                "send_email",
                autospec=True,
                wraps=IrMail_Server,
                side_effect=send_email_origin,
            ) as send_email_mocked,
            patch.object(
                MailMail,
                "create",
                autospec=True,
                wraps=MailMail,
                side_effect=_mail_mail_create,
            ) as mail_mail_create_mocked,
            patch.object(
                MailMail,
                "_send",
                autospec=True,
                wraps=MailMail,
                side_effect=mail_private_send_origin,
            ) as mail_mail_private_send_mocked,
            patch.object(
                MailMail,
                "unlink",
                autospec=True,
                wraps=MailMail,
                side_effect=_mail_mail_unlink,
            ),
            self._patch_push_to_end_point() as patched_push,
        ):
            self.build_email_mocked = build_email_mocked
            self.send_email_mocked = send_email_mocked
            self.mail_mail_create_mocked = mail_mail_create_mocked
            self.mail_mail_private_send_mocked = mail_mail_private_send_mocked
            self.push_to_end_point_mocked = patched_push
            yield

    def _init_mail_mock(self):
        self._mails = []
        self._new_mails = self.env["mail.mail"].sudo()

    @classmethod
    def _init_mail_gateway(cls):
        super()._init_mail_gateway()
        cls.alias_domain = "test.mycompany.com"
        cls.alias_catchall = "catchall.test"
        cls.alias_bounce = "bounce.test"
        cls.default_from = "notifications.test"
        cls.default_from_filter = False
        cls.env["ir.config_parameter"].set_param(
            "mail.default.from_filter", cls.default_from_filter
        )

        cls.env["mail.alias.domain"].search([]).write({"sequence": 9999})
        cls.mail_alias_domain = cls._init_alias_domain(
            cls.alias_domain,
            {
                "bounce_alias": cls.alias_bounce,
                "catchall_alias": cls.alias_catchall,
                "company_ids": [(4, cls.env.ref("base.user_admin").company_id.id)],
                "default_from": cls.default_from,
                "name": cls.alias_domain,
                "sequence": 1,
            },
        )
        if cls._mc_enabled:
            cls.alias_bounce_c2 = "bounce.c2"
            cls.alias_catchall_c2 = "catchall.c2"
            cls.alias_default_from_c2 = "notifications.c2"
            cls.alias_domain_c2_name = "test.mycompany2.com"
            cls.mail_alias_domain_c2 = cls._init_alias_domain(
                cls.alias_domain_c2_name,
                {
                    "bounce_alias": cls.alias_bounce_c2,
                    "catchall_alias": cls.alias_catchall_c2,
                    "company_ids": [(4, cls.company_2.id)],
                    "default_from": cls.alias_default_from_c2,
                    "name": cls.alias_domain_c2_name,
                    "sequence": 2,
                },
            )

            cls.alias_bounce_c3 = "bounce.c3"
            cls.alias_catchall_c3 = "catchall.c3"
            cls.alias_default_from_c3 = "notifications.c3"
            cls.alias_domain_c3_name = "test.mycompany3.com"
            cls.mail_alias_domain_c3 = cls._init_alias_domain(
                cls.alias_domain_c3_name,
                {
                    "bounce_alias": cls.alias_bounce_c3,
                    "catchall_alias": cls.alias_catchall_c3,
                    "company_ids": [(4, cls.company_3.id)],
                    "default_from": cls.alias_default_from_c3,
                    "name": cls.alias_domain_c3_name,
                    "sequence": 3,
                },
            )

        cls.mailer_daemon_email = formataddr(
            ("MAILER-DAEMON", f"{cls.alias_bounce}@{cls.alias_domain}")
        )

    @classmethod
    def _init_alias_domain(cls, name, values):
        alias_domain = cls.env["mail.alias.domain"].search([("name", "=", name)])
        if alias_domain:
            alias_domain.write(values)
        else:
            alias_domain = cls.env["mail.alias.domain"].create(values)
        return alias_domain

    def format(
        self,
        template,
        to="groups@example.com, other@gmail.com",
        subject="Frogs",
        email_from="Sylvie Lelitre <test.sylvie.lelitre@agrolait.com>",
        return_path="",
        cc="",
        extra="",
        msg_id="<1198923581.41972151344608186760.JavaMail@agrolait.com>",
        references="",
        date="Fri, 10 Aug 2012 14:16:26 +0000",
        **kwargs,
    ):
        if not return_path:
            return_path = "<whatever-2a840@postmaster.twitter.com>"
        return template.format(
            subject=subject,
            to=to,
            cc=cc,
            email_from=email_from,
            return_path=return_path,
            extra=extra,
            msg_id=msg_id,
            references=references,
            date=date,
            **kwargs,
        )

    def format_and_process(
        self,
        template,
        email_from,
        to,
        subject="Frogs",
        cc="",
        return_path="",
        extra="",
        msg_id=False,
        model=None,
        target_model="mail.test.gateway",
        target_field="name",
        with_user=None,
        **kwargs,
    ):
        self.assertFalse(self.env[target_model].search([(target_field, "=", subject)]))
        if not msg_id:
            msg_id = "<%.7f-%05d-test@iron.sky>" % (time.time(), randint(0, 99998))

        if kwargs.pop("debug_log", False):
            _logger.info(
                "-- Simulate routing --\n-From: %s (Return-Path %s)\n-To: %s / CC: %s\n-Message-Id: %s / Extra: %s",
                email_from,
                return_path,
                to,
                cc,
                msg_id,
                extra,
            )
        mail = self.format(
            template,
            to=to,
            subject=subject,
            cc=cc,
            return_path=return_path,
            extra=extra,
            email_from=email_from,
            msg_id=msg_id,
            **kwargs,
        )
        self.env["mixin.mail.thread"].with_user(
            with_user or self.env.user
        ).sudo().message_process(model, mail)
        return self.env[target_model].search([(target_field, "=", subject)])

    def _gateway_mail_reply(
        self,
        template,
        mail=None,
        email=None,
        force_email_from=False,
        force_email_to=False,
        force_return_path=False,
        cc=False,
        extra=False,
        use_references=True,
        extra_references=False,
        use_in_reply_to=False,
        target_model="mail.test.gateway",
        target_field="name",
        debug_log=False,
    ):
        if not mail and not email:
            raise ValueError("Wrong usage of _gateway_mail_reply")
        message_id = (mail and mail.message_id) or email["message_id"]
        original_reply_to = (mail and mail.reply_to) or (email and email["reply_to"])
        original_to = (mail and mail.email_to) or (email and email["email_to"][0])
        original_subject = (mail and mail.subject) or (email and email["subject"])

        extra = f"{extra}\n" if extra else ""
        if use_in_reply_to:
            extra = f"{extra}In-Reply-To:\r\n\t{message_id}\n"
        if use_references:
            extra = f"{extra}References:\r\n\t{message_id}\n"
            if extra_references:
                extra = f"{extra}\r{extra_references}\n"

        return self.format_and_process(
            template,
            force_email_from or original_to,
            force_email_to or original_reply_to,
            cc=cc,
            extra=extra,
            return_path=force_return_path or original_to,
            subject=f"Re: {original_subject}",
            target_field=target_field,
            target_model=target_model,
            debug_log=debug_log,
        )

    def gateway_mail_reply_from_smtp_email(
        self,
        template,
        source_smtp_to_list,
        reply_all=False,
        add_to_lst=False,
        cc=False,
        force_email_from=False,
        force_return_path=False,
        extra=False,
        use_references=True,
        extra_references=False,
        use_in_reply_to=False,
        debug_log=False,
        target_model="mail.test.gateway",
    ):
        smtp_email = next(
            (m for m in self.emails if m["smtp_to_list"] == source_smtp_to_list), False
        )
        if not smtp_email:
            raise AssertionError(f"Not found SMTP email for {source_smtp_to_list}")
        email = next(
            (
                m
                for m in self._mails
                if sorted(email_normalize(addr) for addr in m["email_to"])
                == sorted(source_smtp_to_list)
            ),
            False,
        )
        if not email:
            raise AssertionError(
                f"Not found matching mail.mail for {source_smtp_to_list}"
            )

        if not reply_all:
            replying_to = email["reply_to"]
        else:
            replying_to = ",".join(
                [email["reply_to"]]
                + [
                    email
                    for email in email_split_and_format_normalize(smtp_email["msg_to"])
                    if email_normalize(email) not in source_smtp_to_list
                ]
            )
        if add_to_lst:
            replying_to = f"{replying_to},{','.join(add_to_lst)}"
        with (
            RecordCapturer(self.env["mail.message"]) as capture_messages,
            self.mock_mail_gateway(),
        ):
            self._gateway_mail_reply(
                template,
                email=email,
                force_email_from=force_email_from,
                force_email_to=replying_to,
                force_return_path=force_return_path,
                cc=cc,
                extra=extra,
                use_references=use_references,
                extra_references=extra_references,
                use_in_reply_to=use_in_reply_to,
                debug_log=debug_log,
                target_model=target_model,
            )
        return capture_messages.records

    def gateway_mail_reply_last_email(
        self, template, force_email_to=False, debug_log=False
    ):
        self.assertEqual(len(self._mails), 1)
        email = self._mails[0]
        with (
            RecordCapturer(self.env["mail.message"]) as capture_messages,
            self.mock_mail_gateway(),
        ):
            self._gateway_mail_reply(
                template,
                email=email,
                force_email_to=force_email_to,
                debug_log=debug_log,
            )
        return capture_messages

    def gateway_mail_reply_wrecord(
        self, template, record, use_in_reply_to=True, debug_log=False
    ):
        mail_mail = self._find_mail_mail_wrecord(record)

        if use_in_reply_to:
            disturbing_other_msg_id = False
            use_references = False
        else:
            disturbing_other_msg_id = "<123456.654321@another.host.com>"
            use_references = True
        return self._gateway_mail_reply(
            template,
            mail=mail_mail,
            use_references=use_references,
            extra_references=disturbing_other_msg_id,
            use_in_reply_to=use_in_reply_to,
            target_field=record._rec_name,
            target_model=record._name,
            debug_log=debug_log,
        )

    def gateway_mail_reply_wemail(
        self,
        template,
        email_to,
        target_model=None,
        target_field="name",
        debug_log=False,
    ):
        email = self._find_sent_email_wemail(email_to)
        return self._gateway_mail_reply(
            template,
            email=email,
            use_in_reply_to=True,
            target_field=target_field,
            target_model=target_model,
            debug_log=debug_log,
        )

    def from_string(self, text):
        return email.message_from_string(text, policy=email.policy.SMTP)

    def assertHtmlEqual(self, value, expected, message=None):
        tree = html.fragment_fromstring(
            value, parser=html.HTMLParser(encoding="utf-8"), create_parent="body"
        )

        for base_node in tree.xpath("//base"):
            base_node.getparent().remove(base_node)

        expected_node = html.fragment_fromstring(expected, create_parent="body")

        if message:
            self.assertEqual(tree, expected_node, message)
        else:
            self.assertEqual(tree, expected_node)

    def _find_sent_email(
        self, email_from, emails_to, subject=None, body=None, attachment_names=None
    ):
        sent_emails = [
            mail
            for mail in self._mails
            if set(mail["email_to"]) == set(emails_to)
            and mail["email_from"] == email_from
        ]
        if len(sent_emails) > 1:
            sent_email = next(
                (
                    mail
                    for mail in sent_emails
                    if (subject is None or mail["subject"] == subject)
                    and (body is None or mail["body"] == body)
                    and (
                        attachment_names is None
                        or set(attachment_names)
                        == {attachment[0] for attachment in mail["attachments"]}
                    )
                ),
                False,
            )
        else:
            sent_email = sent_emails[0] if sent_emails else False

        if not sent_email:
            debug_info = "\n".join(
                f"From: {mail['email_from']} - To {mail['email_to']}"
                for mail in self._mails
            )
            raise AssertionError(
                f"sent mail not found for email_to {emails_to} from {email_from}"
                f"(optional: subject {subject})"
                f"\n--MOCK DATA\n{debug_info}"
            )

        return sent_email

    def _find_sent_email_wemail(self, email_to):
        for sent_email in self._mails:
            if set(sent_email["email_to"]) == {email_to}:
                break
        else:
            debug_info = "\n".join(
                f"From: {mail['email_from']} - To {mail['email_to']}"
                for mail in self._mails
            )
            raise AssertionError(
                f"sent mail not found for email_to {email_to}\n{debug_info}"
            )
        return sent_email

    def _filter_mail(
        self, status=None, mail_message=None, author=None, content=None, email_from=None
    ):
        filtered = self._new_mails.env["mail.mail"]
        for mail in self._new_mails:
            if status is not None and mail.state != status:
                continue
            if mail_message is not None and mail.mail_message_id != mail_message:
                continue
            if author is not None and mail.author_id != author:
                continue
            if content is not None and content not in mail.body_html:
                continue
            if email_from is not None and mail.email_from != email_from:
                continue
            filtered += mail
        return filtered

    def _find_mail_mail_wid(
        self,
        mail_id,
        status=None,
        mail_message=None,
        author=None,
        content=None,
        email_from=None,
    ):
        filtered = self._filter_mail(
            status=status,
            mail_message=mail_message,
            author=author,
            content=content,
            email_from=email_from,
        )
        for mail in filtered:
            if mail.id == mail_id:
                break
        else:
            debug_info = "\n".join(
                f"From: {mail.author_id} ({mail.email_from}) - ID {mail.id} (State: {mail.state})"
                for mail in self._new_mails
            )
            raise AssertionError(
                f"mail.mail not found for ID {mail_id} / message {mail_message} / status {status} / "
                f"author {author} ({email_from})\n{debug_info}"
            )
        return mail

    def _find_mail_mail_wpartners(
        self,
        recipients,
        status,
        mail_message=None,
        author=None,
        content=None,
        email_from=None,
    ):
        filtered = self._filter_mail(
            status=status,
            mail_message=mail_message,
            author=author,
            content=content,
            email_from=email_from,
        )
        for mail in filtered:
            if all(p in mail.recipient_ids for p in recipients):
                break
        else:
            debug_info = "\n".join(
                f"From: {mail.author_id} ({mail.email_from}) - To: {sorted(mail.recipient_ids.ids)} (State: {mail.state})"
                for mail in self._new_mails
            )
            author_info = (
                f"{author.name} ({author.id})"
                if isinstance(author, self.env["res.partner"].__class__)
                else author
            )
            recipients_info = f"Missing: {[f'{r.name} ({r.id})' for r in recipients if r.id not in filtered.recipient_ids.ids]}"
            raise AssertionError(
                f"mail.mail not found for message {mail_message} / status {status} / recipients {sorted(recipients.ids)} / "
                f"author {author_info}, email_from ({email_from})\n{recipients_info}\n{debug_info}"
            )
        return mail

    def _find_mail_mail_wemail(
        self,
        email_to,
        status,
        mail_message=None,
        author=None,
        content=None,
        email_from=None,
    ):
        filtered = self._filter_mail(
            status=status,
            mail_message=mail_message,
            author=author,
            content=content,
            email_from=email_from,
        )
        for mail in filtered:
            if (mail.email_to == email_to and not mail.recipient_ids) or (
                not mail.email_to and mail.recipient_ids.email == email_to
            ):
                break
        else:
            debug_info = "\n".join(
                f"From: {mail.author_id} ({mail.email_from}) - To: {mail.email_to} / {sorted(mail.recipient_ids.mapped('email'))} (State: {mail.state})"
                for mail in self._new_mails
            )
            raise AssertionError(
                f"mail.mail not found for message {mail_message} / status {status} / email_to {email_to} / "
                f"author {author} ({email_from})\n-- MOCK DATA\n{debug_info}"
            )
        return mail

    def _find_mail_mail_wrecord(
        self,
        record,
        status=None,
        mail_message=None,
        author=None,
        content=None,
        email_from=None,
    ):
        filtered = self._filter_mail(
            status=status,
            mail_message=mail_message,
            author=author,
            content=content,
            email_from=email_from,
        )
        for mail in filtered:
            if mail.model == record._name and mail.res_id == record.id:
                break
        else:
            debug_info = "\n".join(
                f"From: {mail.author_id} ({mail.email_from}) - Model {mail.model} / ResId {mail.res_id} (State: {mail.state})"
                for mail in self._new_mails
            )
            raise AssertionError(
                f"mail.mail not found for message {mail_message} / status {status} / record {record._name}, {record.id} / author {author} ({email_from})\n{debug_info}"
            )
        return mail

    def _assertMailMail(
        self,
        mail,
        recipients_list,
        status,
        email_to_all=None,
        email_to_recipients=None,
        author=None,
        content=None,
        fields_values=None,
        email_values=None,
    ):
        self.assertTrue(bool(mail))
        if content:
            self.assertIn(content, mail.body_html)

        references_message_id_check = (email_values or {}).pop(
            "references_message_id_check", False
        )
        if references_message_id_check:
            message_id = mail["message_id"]
            self.assertTrue(message_id, "Mail: expected value set for message_id")
            self.assertIn(
                message_id,
                mail.references,
                "Mail: expected message_id to be part of references",
            )
            email_values = dict(
                {"message_id": message_id, "references": mail.references},
                **(email_values or {}),
            )

        for fname, expected_fvalue in (fields_values or {}).items():
            with self.subTest(fname=fname, expected_fvalue=expected_fvalue):
                if fname == "headers":
                    fvalue = mail[fname] or {}
                    if "X-Msg-To-Add" in fvalue and "X-Msg-To-Add" in expected_fvalue:
                        msg_to_add = fvalue["X-Msg-To-Add"]
                        exp_msg_to_add = expected_fvalue["X-Msg-To-Add"]
                        self.assertEqual(
                            sorted(email_split_and_format_normalize(msg_to_add)),
                            sorted(email_split_and_format_normalize(exp_msg_to_add)),
                        )
                        fvalue = dict(fvalue)
                        fvalue.pop("X-Msg-To-Add")
                        expected_fvalue = dict(expected_fvalue)
                        expected_fvalue.pop("X-Msg-To-Add")
                        self.assertDictEqual(fvalue, expected_fvalue)
                    else:
                        self.assertDictEqual(fvalue, expected_fvalue)
                elif fname == "attachments_info":
                    for attachment_info in expected_fvalue:
                        attachment = next(
                            (
                                attach
                                for attach in mail.attachment_ids
                                if attach.name == attachment_info["name"]
                            ),
                            False,
                        )
                        self.assertTrue(
                            bool(attachment),
                            f"Attachment {attachment_info['name']} not found in attachments",
                        )
                        if attachment_info.get("raw"):
                            self.assertEqual(attachment[1], attachment_info["raw"])
                        if attachment_info.get("type"):
                            self.assertEqual(attachment[2], attachment_info["type"])
                    self.assertEqual(len(expected_fvalue), len(mail.attachment_ids))
                else:
                    self.assertEqual(
                        mail[fname],
                        expected_fvalue,
                        "Mail: expected %s for %s, got %s"
                        % (expected_fvalue, fname, mail[fname]),
                    )
        if status == "sent":
            if email_to_recipients:
                recipients = email_to_recipients
            else:
                recipients = [[r] for r in recipients_list]
            for recipient in recipients:
                with self.subTest(recipient=recipient):
                    self.assertSentEmail(
                        email_values["email_from"]
                        if email_values and email_values.get("email_from")
                        else author,
                        recipient,
                        **(email_values or {}),
                    )
            if email_to_all:
                self.assertSentEmail(
                    email_values["email_from"]
                    if email_values and email_values.get("email_from")
                    else author,
                    email_to_all,
                    **(email_values or {}),
                )

    def assertMailMail(
        self,
        recipients,
        status,
        email_to_recipients=None,
        email_to_all=None,
        mail_message=None,
        author=None,
        content=None,
        fields_values=None,
        email_values=None,
    ):
        email_from = (fields_values or {}).get("email_from")
        if recipients:
            found_mail = self._find_mail_mail_wpartners(
                recipients,
                status,
                mail_message=mail_message,
                author=author,
                content=content,
                email_from=email_from,
            )
        else:
            mail_email_to = ",".join(email_to_all)
            found_mail = self._find_mail_mail_wemail(
                mail_email_to,
                status,
                mail_message=mail_message,
                author=author,
                content=content,
                email_from=email_from,
            )

        self.assertTrue(bool(found_mail))
        self._assertMailMail(
            found_mail,
            recipients,
            status,
            email_to_recipients=email_to_recipients,
            author=author,
            content=content,
            email_to_all=email_to_all,
            fields_values=fields_values,
            email_values=email_values,
        )
        return found_mail

    def assertMailMailWEmails(
        self,
        emails,
        status,
        email_to_recipients=None,
        mail_message=None,
        author=None,
        content=None,
        fields_values=None,
        email_values=None,
    ):
        found_mail = False
        for email_to in emails:
            found_mail = self._find_mail_mail_wemail(
                email_to,
                status,
                mail_message=mail_message,
                author=author,
                content=content,
                email_from=(fields_values or {}).get("email_from"),
            )
            self.assertTrue(bool(found_mail))
            self._assertMailMail(
                found_mail,
                [email_to],
                status,
                email_to_recipients=email_to_recipients,
                author=author,
                content=content,
                fields_values=fields_values,
                email_values=email_values,
            )
        return found_mail

    def assertMailMailWRecord(
        self,
        record,
        recipients,
        status,
        email_to_recipients=None,
        mail_message=None,
        author=None,
        content=None,
        fields_values=None,
        email_values=None,
    ):
        found_mail = self._find_mail_mail_wrecord(
            record,
            status,
            mail_message=mail_message,
            author=author,
            content=content,
            email_from=(fields_values or {}).get("email_from"),
        )
        self.assertTrue(bool(found_mail))
        self._assertMailMail(
            found_mail,
            recipients,
            status,
            email_to_recipients=email_to_recipients,
            author=author,
            content=content,
            fields_values=fields_values,
            email_values=email_values,
        )
        return found_mail

    def assertMailMailWId(
        self,
        mail_id,
        status,
        email_to_recipients=None,
        author=None,
        content=None,
        fields_values=None,
        email_values=None,
    ):
        found_mail = self._find_mail_mail_wid(mail_id)
        self.assertTrue(bool(found_mail))
        self._assertMailMail(
            found_mail,
            [],
            status,
            email_to_recipients=email_to_recipients,
            author=author,
            content=content,
            fields_values=fields_values,
            email_values=email_values,
        )
        return found_mail

    def assertMessageFields(self, message, fields_values):
        for fname, fvalue in fields_values.items():
            with self.subTest(fname=fname, fvalue=fvalue):
                if fname in {"incoming_email_cc", "incoming_email_to"}:
                    self.assertEqual(
                        sorted(
                            tools.mail.email_split_and_format_normalize(message[fname])
                        ),
                        sorted(tools.mail.email_split_and_format_normalize(fvalue)),
                        f"Message: expected {fvalue} for {fname}, got {message[fname]}",
                    )
                elif fname == "tracking_field_names":
                    found = message.sudo().mapped("tracking_value_ids.field_id.name")
                    self.assertEqual(
                        sorted(found),
                        sorted(fvalue),
                        f"Message: expected {fvalue} for {fname}, got {found}",
                    )
                elif fname == "tracking_values":
                    self.assertTracking(message, fvalue, strict=True)
                else:
                    self.assertEqual(
                        message[fname],
                        fvalue,
                        f"Message: expected {fvalue} for {fname}, got {message[fname]}",
                    )

    def assertNoMail(self, recipients, email_to=None, mail_message=None, author=None):
        try:
            if recipients:
                self._find_mail_mail_wpartners(
                    recipients, None, mail_message=mail_message, author=author
                )
            elif email_to is not None:
                self._find_mail_mail_wemail(
                    email_to, None, mail_message=mail_message, author=author
                )
        except AssertionError:
            pass
        else:
            raise AssertionError(
                "mail.mail exists for message %s / recipients %s / emails %s but should not exist"
                % (mail_message, recipients.ids, email_to or "/")
            )
        finally:
            self.assertNotSentEmail(
                recipients=list(recipients)
                + email_split_and_format_normalize(email_to or ""),
                message_id=mail_message and mail_message.message_id,
            )

    def assertNotSentEmail(self, recipients=None, message_id=None):
        mails = self._mails
        if message_id:
            mails = [mail for mail in self._mails if mail["message_id"] == message_id]
        if recipients:
            all_emails = [
                email_to.email_formatted
                if isinstance(email_to, self.env["res.partner"].__class__)
                else email_to
                for email_to in recipients
            ]

            mails = [
                mail
                for mail in mails
                if any(email in all_emails for email in mail["email_to"])
            ]

        self.assertEqual(len(mails), 0)

    def _prepare_expected_sent_email(self, author, recipients, values, known_fields):
        unknown = set(values.keys()) - set(known_fields)
        if unknown:
            raise NotImplementedError("Unsupported %s" % ", ".join(unknown))

        expected = {fname: values[fname] for fname in known_fields if fname in values}
        if isinstance(author, self.env["res.partner"].__class__):
            expected["email_from"] = formataddr(
                (
                    author.name,
                    email_normalize(author.email, strict=False) or author.email,
                )
            )
        else:
            expected["email_from"] = author

        if "email_to" in values:
            email_to_list = values["email_to"]
        else:
            email_to_list = []
            for email_to in recipients:
                if isinstance(email_to, self.env["res.partner"].__class__):
                    email_to_list.append(
                        formataddr(
                            (
                                email_to.name,
                                email_normalize(email_to.email, strict=False)
                                or email_to.email,
                            )
                        )
                    )
                else:
                    email_to_list.append(email_to)
        expected["email_to"] = email_to_list
        return expected

    def _assert_sent_email_attachments(self, expected, sent_mail):
        if "attachments" in expected:
            self.assertEqual(
                sorted(expected["attachments"]),
                sorted(sent_mail["attachments"]),
                "Value for %s: expected %s, received %s"
                % ("attachments", expected["attachments"], sent_mail["attachments"]),
            )
        if "attachments_info" in expected:
            attachments = sent_mail["attachments"]
            for attachment_info in expected["attachments_info"]:
                attachment = next(
                    (
                        attach
                        for attach in attachments
                        if attach[0] == attachment_info["name"]
                    ),
                    False,
                )
                self.assertTrue(
                    bool(attachment),
                    f"Attachment {attachment_info['name']} not found in attachments",
                )
                if attachment_info.get("raw"):
                    self.assertEqual(attachment[1], attachment_info["raw"])
                if attachment_info.get("type"):
                    self.assertEqual(attachment[2], attachment_info["type"])
            self.assertEqual(len(expected["attachments_info"]), len(attachments))
        if "body" in expected:
            self.assertHtmlEqual(
                expected["body"],
                sent_mail["body"],
                "Value for %s: expected %s, received %s"
                % ("body", expected["body"], sent_mail["body"]),
            )

    def _assert_sent_email_headers(self, expected, sent_mail):
        if "headers" not in expected:
            return
        if (
            "X-Msg-To-Add" in sent_mail["headers"]
            and "X-Msg-To-Add" in expected["headers"]
        ):
            msg_to_add = sent_mail["headers"]["X-Msg-To-Add"]
            exp_msg_to_add = expected["headers"]["X-Msg-To-Add"]
            self.assertEqual(
                sorted(email_split_and_format_normalize(msg_to_add)),
                sorted(email_split_and_format_normalize(exp_msg_to_add)),
            )
        for key, value in expected["headers"].items():
            if key == "X-Msg-To-Add":
                continue
            self.assertTrue(key in sent_mail["headers"], f"Missing key {key}")
            found = sent_mail["headers"][key]
            self.assertEqual(
                found,
                value,
                f"Header value for {key} invalid, found {found} instead of {value}",
            )

    def assertSentEmail(self, author, recipients, **values):
        direct_check = [
            "body_alternative",
            "email_from",
            "message_id",
            "references",
            "reply_to",
            "subject",
        ]
        content_check = [
            "body_alternative_content",
            "body_content",
            "references_content",
        ]
        email_list_check = ["email_bcc", "email_cc", "email_to"]
        other_check = ["attachments", "attachments_info", "body", "headers"]

        expected = self._prepare_expected_sent_email(
            author,
            recipients,
            values,
            direct_check + content_check + email_list_check + other_check,
        )

        attachments = [
            attachment["name"]
            for attachment in values.get("attachments_info", [])
            if "name" in attachment
        ]
        sent_mail = self._find_sent_email(
            expected["email_from"],
            expected["email_to"],
            subject=values.get("subject"),
            body=values.get("body"),
            attachment_names=attachments or None,
        )
        debug_info = ""
        if not sent_mail:
            debug_info = "\n-".join(
                "From: %s-To: %s" % (mail["email_from"], mail["email_to"])
                for mail in self._mails
            )
        self.assertTrue(
            bool(sent_mail),
            "Expected mail from %s to %s not found in %s\n"
            % (expected["email_from"], expected["email_to"], debug_info),
        )

        for val in direct_check:
            if val in expected:
                self.assertEqual(
                    expected[val],
                    sent_mail[val],
                    "Value for %s: expected %s, received %s"
                    % (val, expected[val], sent_mail[val]),
                )
        self._assert_sent_email_attachments(expected, sent_mail)

        for val in email_list_check:
            if expected.get(val):
                self.assertEqual(
                    sorted(expected[val]),
                    sorted(sent_mail[val]),
                    "Value for %s: expected %s, received %s"
                    % (val, expected[val], sent_mail[val]),
                )
            elif val in expected:
                self.assertEqual(
                    expected[val],
                    sent_mail[val],
                    "Value for %s: expected %s, received %s"
                    % (val, expected[val], sent_mail[val]),
                )

        for val in content_check:
            if val == "references_content" and val in expected:
                if not expected["references_content"]:
                    self.assertFalse(sent_mail["references"])
                else:
                    for reference in expected["references_content"]:
                        self.assertIn(reference, sent_mail["references"])
            elif val in expected:
                self.assertIn(
                    expected[val],
                    sent_mail[val[:-8]],
                    "Value for %s: %s does not contain %s"
                    % (val, sent_mail[val[:-8]], expected[val]),
                )

        self._assert_sent_email_headers(expected, sent_mail)
        return sent_mail

    def assertNoPushNotification(self):
        self.push_to_end_point_mocked.assert_not_called()
        self.assertEqual(self.env["mail.push"].search_count([]), 0)

    def assertPushNotification(
        self,
        mail_push_count=0,
        endpoint=None,
        keys=None,
        title=None,
        title_content=None,
        body=None,
        body_content=None,
        options=None,
    ):
        self.push_to_end_point_mocked.assert_called_once()
        self.assertEqual(self.env["mail.push"].search_count([]), mail_push_count)
        if endpoint:
            self.assertEqual(
                self.push_to_end_point_mocked.call_args.kwargs["device"]["endpoint"],
                endpoint,
            )
        if keys:
            private, public = keys
            self.assertIn(private, self.push_to_end_point_mocked.call_args.kwargs)
            self.assertIn(public, self.push_to_end_point_mocked.call_args.kwargs)
        payload_value = json.loads(
            self.push_to_end_point_mocked.call_args.kwargs["payload"]
        )
        if title_content:
            self.assertIn(title_content, payload_value["title"])
        elif title:
            self.assertEqual(title, payload_value["title"])
        if body_content:
            self.assertIn(body_content, payload_value["options"]["body"])
        elif body:
            self.assertEqual(body, payload_value["options"]["body"])
        if options:
            payload_options = payload_value["options"]
            for key, val in options.items():
                with self.subTest(key=key):
                    self.assertEqual(payload_options[key], val)

    def assertTracking(self, message, data, strict=False):
        tracking_values = message.sudo().tracking_value_ids
        if strict:
            self.assertEqual(
                len(tracking_values), len(data), "Tracking: tracking does not match"
            )

        suffix_mapping = {
            "boolean": "integer",
            "char": "char",
            "date": "datetime",
            "datetime": "datetime",
            "integer": "integer",
            "float": "float",
            "many2many": "char",
            "one2many": "char",
            "selection": "char",
            "text": "text",
        }
        for field_name, value_type, old_value, new_value in data:
            tracking = tracking_values.filtered(
                lambda track, field_name=field_name: track.field_id.name == field_name
            )
            self.assertEqual(len(tracking), 1, f"Tracking: not found for {field_name}")
            msg_base = f"Tracking: {field_name} ({value_type}: "
            if value_type in suffix_mapping:
                old_value_fname = f"old_value_{suffix_mapping[value_type]}"
                new_value_fname = f"new_value_{suffix_mapping[value_type]}"
                self.assertEqual(
                    tracking[old_value_fname],
                    old_value,
                    msg_base
                    + f"expected {old_value}, received {tracking[old_value_fname]})",
                )
                self.assertEqual(
                    tracking[new_value_fname],
                    new_value,
                    msg_base
                    + f"expected {new_value}, received {tracking[new_value_fname]})",
                )
            if value_type == "many2one":
                self.assertEqual(
                    tracking.old_value_integer, (old_value and old_value.id) or False
                )
                self.assertEqual(
                    tracking.new_value_integer, (new_value and new_value.id) or False
                )
                self.assertEqual(
                    tracking.old_value_char,
                    (old_value and old_value.display_name) or "",
                )
                self.assertEqual(
                    tracking.new_value_char,
                    (new_value and new_value.display_name) or "",
                )
            elif value_type == "monetary":
                new_value, currency = new_value
                self.assertEqual(tracking.currency_id, currency)
                self.assertEqual(tracking.old_value_float, old_value)
                self.assertEqual(tracking.new_value_float, new_value)
            if value_type not in suffix_mapping and value_type not in {
                "many2one",
                "monetary",
            }:
                self.assertEqual(
                    1, 0, f"Tracking: unsupported tracking test on {value_type}"
                )


class MailCase(common.TransactionCase, MockEmail, BusCase):
    _test_context = {
        "mail_create_nolog": True,
        "mail_create_nosubscribe": True,
        "mail_notrack": True,
        "no_reset_password": True,
    }

    def setUp(self):
        super().setUp()
        self.flush_tracking()

    def _mock_smtplib_connection(self):
        smtp = self.mock_smtplib_connection()
        smtp.__enter__()
        self.addCleanup(lambda: smtp.__exit__(None, None, None))

    @classmethod
    def _reset_mail_context(cls, record):
        return record.with_context(
            mail_create_nolog=False,
            mail_create_nosubscribe=False,
            mail_notrack=False,
        )

    def flush_tracking(self):
        self.env.flush_all()
        self.cr.flush()

    @contextmanager
    def mock_bus(self):
        bus_bus_create_origin = BusBus.create
        self._init_mock_bus()

        def _bus_bus_create(model, *args, **kwargs):
            res = bus_bus_create_origin(model, *args, **kwargs)
            self._new_bus_notifs += res.sudo()
            return res

        with patch.object(
            BusBus, "create", autospec=True, wraps=BusBus, side_effect=_bus_bus_create
        ) as _bus_bus_create_mock:
            yield
            self.env.cr.precommit.run()

    def _init_mock_bus(self):
        self._new_bus_notifs = self.env["bus.bus"].sudo()

    @contextmanager
    def mock_mail_app(self):
        message_create_origin = MailMessage.create
        notification_create_origin = MailNotification.create
        self._init_mock_mail()

        def _mail_message_create(model, *args, **kwargs):
            res = message_create_origin(model, *args, **kwargs)
            self._new_msgs += res.sudo()
            return res

        def _mail_notification_create(model, *args, **kwargs):
            res = notification_create_origin(model, *args, **kwargs)
            self._new_notifs += res.sudo()
            return res

        with (
            patch.object(
                MailMessage,
                "create",
                autospec=True,
                wraps=MailMessage,
                side_effect=_mail_message_create,
            ) as _mail_message_create_mock,
            patch.object(
                MailNotification,
                "create",
                autospec=True,
                wraps=MailNotification,
                side_effect=_mail_notification_create,
            ) as _mail_notification_create_mock,
        ):
            yield

    def _init_mock_mail(self):
        self._new_msgs = self.env["mail.message"].sudo()
        self._new_notifs = self.env["mail.notification"].sudo()

    @classmethod
    def _add_messages(cls, record, body_content, count=1, author=None, **kwargs):
        author = author or cls.env.user.partner_id
        if "email_from" not in kwargs:
            kwargs["email_from"] = author.email_formatted
        subtype_id = kwargs.get("subtype_id", cls.env.ref("mail.mt_comment").id)

        values = {
            "model": record._name,
            "res_id": record.id,
            "author_id": author.id,
            "subtype_id": subtype_id,
        }
        values.update(kwargs)

        create_vals = [
            dict(values, body="%s/%02d" % (body_content, counter))
            for counter in range(count)
        ]

        return cls.env["mail.message"].sudo().create(create_vals)

    @classmethod
    def _create_portal_user(cls):
        cls.user_portal = mail_new_test_user(
            cls.env,
            login="portal_test",
            groups="base.group_portal",
            name="Chell Gladys",
            notification_type="email",
        )
        cls.partner_portal = cls.user_portal.partner_id
        return cls.user_portal

    @classmethod
    def _create_records_for_batch(cls, model, count, additional_values=None, prefix=""):
        additional_values = additional_values or {}
        records = cls.env[model]
        partners = cls.env["res.partner"]
        country_id = cls.env.ref("base.be").id

        base_values = [
            {
                "name": f"{prefix}Test_{idx}",
                **additional_values,
            }
            for idx in range(count)
        ]

        partner_fnames = cls.env[model]._mail_get_partner_fields(introspect_fields=True)
        if partner_fname := partner_fnames[0] if partner_fnames else False:
            partners = (
                cls.env["res.partner"]
                .with_context(**cls._test_context)
                .create(
                    [
                        {
                            "name": f"Partner_{idx}",
                            "email": f"{prefix}test_partner_{idx}@example.com",
                            "country_id": country_id,
                            "phone_ids": [
                                Command.create(
                                    {"number": "047500%02d%02d" % (idx, idx)}
                                )
                            ],
                        }
                        for idx in range(count)
                    ]
                )
            )
            for values, partner in zip(base_values, partners, strict=False):
                values[partner_fname] = partner.id

        records = cls.env[model].with_context(**cls._test_context).create(base_values)

        cls.records = cls._reset_mail_context(records)
        cls.partners = partners
        return cls.records, cls.partners

    @classmethod
    def _create_template(cls, model, template_values=None):
        create_values = {
            "name": "TestTemplate",
            "subject": "About {{ object.name }}",
            "body_html": '<p>Hello <t t-out="object.name"/></p>',
            "model_id": cls.env["ir.model"]._get(model).id,
        }
        if template_values:
            create_values.update(template_values)
        cls.email_template = cls.env["mail.template"].create(create_values)
        return cls.email_template

    @staticmethod
    def _generate_attachments_data(
        count, res_model, res_id, attach_values=None, prefix=None
    ):
        attach_values = attach_values or {}
        prefix = prefix or ""
        return [
            {
                "datas": base64.b64encode(b"AttContent_%02d" % x),
                "name": f"{prefix}AttFileName_{x:02d}.txt",
                "mimetype": "text/plain",
                "res_model": res_model,
                "res_id": res_id,
                **attach_values,
            }
            for x in range(count)
        ]

    def _generate_notify_recipients(self, partners, record=None):
        entries = []
        for partner in partners:
            user = partner.user_ids.filtered("active").sorted(
                key=lambda u: (u.share, u.id)
            )[:1]
            entries.append(
                prepare_recipient_data(
                    partner_id=partner.id,
                    active=partner.active,
                    email_normalized=partner.email_normalized,
                    groups=frozenset(user.all_group_ids.ids),
                    is_follower=(
                        partner in record.message_partner_ids if record else False
                    ),
                    lang=partner.lang,
                    name=partner.name,
                    notif=user.notification_type or "email",
                    partner_share=partner.partner_share,
                    uid=user.id,
                    user_share=bool(user.share),
                )
            )
        return entries

    def _get_mail_composer_web_context(self, records, add_web=True, **values):
        base_context = {
            "default_model": records._name,
            "default_res_ids": records.ids,
        }
        if len(records) == 1:
            base_context["default_composition_mode"] = "comment"
        else:
            base_context["default_composition_mode"] = "mass_mail"
        if add_web:
            base_context["active_model"] = records._name
            base_context["active_id"] = records[0].id
            base_context["active_ids"] = records.ids
        if values:
            base_context.update(**values)
        return base_context

    def _message_post_and_get_unfollow_urls(self, record, partner_ids):
        with self.mock_mail_gateway():
            user_admin = self.env.ref("base.user_admin")
            _message = (
                record.with_user(user_admin)
                .with_context(
                    email_notification_force_header=True,
                    email_notification_force_footer=True,
                )
                .message_post(
                    body="test message",
                    partner_ids=partner_ids.ids,
                    subtype_id=self.env.ref("mail.mt_comment").id,
                )
            )
        self.assertEqual(len(self._mails), len(partner_ids))
        mail_by_email = {
            email_normalize(email_to, strict=False): mail
            for mail in self._mails
            for email_to in mail["email_to"]
        }

        results = []
        for partner in partner_ids:
            mail_body = mail_by_email[partner.email_normalized]["body"]
            unfollow_urls = [
                link_url
                for _, link_url, _, _ in tools.mail.HTML_TAG_URL_REGEX.findall(
                    mail_body
                )
                if "/mail/unfollow" in link_url
            ]
            self.assertLessEqual(len(unfollow_urls), 1)
            results.append(unfollow_urls[0] if unfollow_urls else False)
        self.assertEqual(len(results), len(partner_ids))
        return results

    def _setup_out_of_office(self, users, ooo_from=None, ooo_to=None):
        now = self.env.cr.now()
        users.sudo().write(
            {
                "out_of_office_message": Markup(
                    "<p>Le numéro que vous avez composé n'est plus attribué.</p>"
                ),
                "out_of_office_from": ooo_from or now - timedelta(days=1),
                "out_of_office_to": ooo_to or now + timedelta(days=10),
            }
        )

    def _url_update_query_parameters(self, url, **kwargs):
        parsed_url = urlparse(url)
        return parsed_url._replace(
            query=urlencode(dict(parse_qsl(parsed_url.query), **kwargs))
        ).geturl()

    @contextmanager
    def assertSinglePostNotifications(
        self, recipients_info, message_info=None, mail_unlink_sent=False
    ):
        r_info = dict(message_info or {})
        r_info.setdefault("content", "")
        r_info["notif"] = recipients_info
        with self.assertPostNotifications([r_info], mail_unlink_sent=mail_unlink_sent):
            yield

    @contextmanager
    def assertPostNotifications(self, recipients_info, mail_unlink_sent=False):
        try:
            with (
                self.mock_mail_gateway(mail_unlink_sent=mail_unlink_sent),
                self.mock_bus(),
                self.mock_mail_app(),
            ):
                yield
        finally:
            done_msgs, done_notifs = self.assertMailNotifications(
                self._new_msgs, recipients_info
            )
            self.assertEqual(
                self._new_msgs,
                done_msgs,
                "Mail: invalid message creation (%s) / expected (%s)"
                % (len(self._new_msgs), len(done_msgs)),
            )
            self.assertEqual(
                self._new_notifs,
                done_notifs,
                "Mail: invalid notification creation (%s) / expected (%s)"
                % (len(self._new_notifs), len(done_notifs)),
            )

    @contextmanager
    def assertBus(self, channels=None, message_items=None, get_params=None):
        def format_notif(notif):
            if not notif.message:
                return ""
            return f"{tuple(json.loads(notif.channel))},  # {json.loads(notif.message).get('type')}"

        def notif_to_string(notif):
            return f"{format_notif(notif)}\n{notif.message}"

        self._reset_bus()
        try:
            with self.mock_bus():
                yield
        finally:
            if get_params:
                channels, message_items = get_params()
            found_bus_notifs = self.assertBusNotifications(
                channels, message_items=message_items
            )
            new_lines = "\n\n"
            self.assertEqual(
                self._new_bus_notifs,
                found_bus_notifs,
                f"\n\nExpected:\n{new_lines[0].join(found_bus_notifs.mapped(format_notif))}"
                f"\n\nResult:\n{new_lines.join(self._new_bus_notifs.mapped(notif_to_string))}",
            )

    @contextmanager
    def assertMsgWithoutNotifications(self, mail_unlink_sent=False):
        try:
            with (
                self.mock_mail_gateway(mail_unlink_sent=mail_unlink_sent),
                self.mock_bus(),
                self.mock_mail_app(),
            ):
                yield
        finally:
            self.assertTrue(self._new_msgs)
            self.assertFalse(bool(self._new_notifs))
            self.assertFalse(bool(self._new_mails))
            self.assertFalse(bool(self._mails))

    @contextmanager
    def assertNoNotifications(self):
        try:
            with (
                self.mock_mail_gateway(mail_unlink_sent=False),
                self.mock_bus(),
                self.mock_mail_app(),
            ):
                yield
        finally:
            self.assertFalse(bool(self._new_msgs))
            self.assertFalse(bool(self._new_notifs))

    def _find_expected_notifications(self, messages, recipients_info):
        partners = (
            self.env["res.partner"]
            .sudo()
            .concat(
                *[
                    p["partner"]
                    for i in recipients_info
                    for p in i["notif"]
                    if p.get("partner")
                ]
            )
        )
        email_addrs = [
            email
            for i in recipients_info
            for p in i["notif"]
            for email in p.get("email_to", [])
            if not p.get("partner")
        ]
        base_domain = [
            "|",
            ("res_partner_id", "in", partners.ids),
            ("mail_email_address", "in", email_addrs),
        ]
        if messages is not None:
            base_domain += [("mail_message_id", "in", messages.ids)]
        notifications = self.env["mail.notification"].sudo().search(base_domain)
        debug_info = "\n-".join(
            f"Notif: partner {notif.res_partner_id.id} ({notif.res_partner_id.name}) / type {notif.notification_type}"
            for notif in notifications
        )
        return notifications, email_addrs, debug_info

    def _find_notified_message(self, messages, mbody, mtype, msubtype):
        if messages:
            message = messages.filtered(
                lambda message: (
                    mbody in message.body
                    and message.message_type == mtype
                    and msubtype == message.subtype_id
                )
            )
            debug_info = "\n".join(
                f"Msg: message_type {message.message_type}, subtype {message.subtype_id.name}, content {message.body}"
                for message in messages
            )
            return message, debug_info
        message = (
            self.env["mail.message"]
            .sudo()
            .search(
                [
                    ("body", "ilike", mbody),
                    ("message_type", "=", mtype),
                    ("subtype_id", "=", msubtype.id),
                ],
                limit=1,
                order="id DESC",
            )
        )
        return message, ""

    def _get_recipient_notif_group(self, partner, email_to_lst):
        if (partner and not partner.user_ids) or (not partner and email_to_lst):
            return "customer"
        if partner and partner.partner_share:
            return "portal"
        return "user"

    def _find_recipient_notif(
        self, notifications, message, partner, email_to_lst, ntype
    ):
        return notifications.filtered(
            lambda n: (
                n.mail_message_id == message
                and (
                    (partner and n.res_partner_id == partner)
                    or n.mail_email_address in email_to_lst
                )
                and n.notification_type == ntype
            )
        )

    def _update_notif_email_groups(
        self,
        email_group,
        status_groups,
        recipient,
        partner,
        email_to_lst,
        email_cc_lst,
        nstatus,
    ):
        if nstatus in ("sent", "ready", "exception") and recipient.get(
            "check_send", True
        ):
            email_group["partners"] += partner
            if "email_to_recipients" in recipient:
                email_group["email_to_recipients"] += recipient["email_to_recipients"]
            if email_cc_lst:
                email_group["email_cc_lst"] += email_cc_lst
            if email_to_lst:
                email_group["email_to_lst"] += email_to_lst
        if nstatus in ("ready", "exception"):
            state = "outgoing" if nstatus == "ready" else "exception"
            if partner:
                status_groups[state]["partners"].append(partner)
            if email_cc_lst:
                status_groups[state]["email_lst"] += email_cc_lst
            if email_to_lst:
                status_groups[state]["email_lst"] += email_to_lst
        elif nstatus in ("sent", "canceled"):
            pass
        else:
            raise NotImplementedError

    def _assert_recipient_notif(
        self, message, recipient, notifications, email_groups, status_groups, debug_info
    ):
        extra_keys = set(recipient.keys()) - {
            "check_send",
            "email_to",
            "email_to_recipients",
            "is_read",
            "failure_reason",
            "failure_type",
            "group",
            "partner",
            "status",
            "type",
        }
        if extra_keys:
            raise ValueError(f"Unsupported recipient values: {extra_keys}")

        partner = recipient.get("partner", self.env["res.partner"])
        email_to_lst, email_cc_lst = (
            recipient.get("email_to", []),
            recipient.get("email_cc", []),
        )
        ntype, nstatus = recipient["type"], recipient.get("status", "sent")
        ngroup = recipient.get("group") or self._get_recipient_notif_group(
            partner, email_to_lst
        )
        if ngroup not in email_groups:
            email_groups[ngroup] = {
                "email_cc_lst": [],
                "email_to_lst": [],
                "email_to_recipients": [],
                "partners": self.env["res.partner"].sudo(),
            }

        notif = self._find_recipient_notif(
            notifications, message, partner, email_to_lst, ntype
        )
        self.assertEqual(
            len(notif),
            1,
            f"Mail: not found notification for {partner or email_to_lst} (type: {ntype}, message: {message.id})\n{debug_info}",
        )
        self.assertEqual(notif.author_id, notif.mail_message_id.author_id)
        self.assertEqual(notif.is_read, recipient.get("is_read", ntype != "inbox"))
        if "failure_reason" in recipient:
            self.assertEqual(notif.failure_reason, recipient["failure_reason"])
        if "failure_type" in recipient:
            self.assertEqual(notif.failure_type, recipient["failure_type"])
        self.assertEqual(notif.notification_status, nstatus)

        if ntype == "email":
            self._update_notif_email_groups(
                email_groups[ngroup],
                status_groups,
                recipient,
                partner,
                email_to_lst,
                email_cc_lst,
                nstatus,
            )
        return notif

    def _get_notif_group_mail_status(self, partners, email_to_lst, status_groups):
        mail_status = "sent"
        if partners and all(
            p in status_groups["exception"]["partners"] for p in partners
        ):
            mail_status = "exception"
        if email_to_lst and all(
            p in status_groups["exception"]["email_lst"] for p in email_to_lst
        ):
            mail_status = "exception"
        if partners and all(
            p in status_groups["outgoing"]["partners"] for p in partners
        ):
            mail_status = "outgoing"
        if email_to_lst and all(
            p in status_groups["outgoing"]["email_lst"] for p in email_to_lst
        ):
            mail_status = "outgoing"
        return mail_status

    def _assert_notif_email_group(
        self, message, message_info, group, status_groups, email_values, mbody
    ):
        partners = group["partners"]
        email_to_lst = group["email_to_lst"]
        mail_status = self._get_notif_group_mail_status(
            partners, email_to_lst, status_groups
        )
        if not self.mail_unlink_sent and (partners or email_to_lst):
            self.assertMailMail(
                partners,
                mail_status,
                author=message_info.get("mail_mail_values", {}).get(
                    "author_id", message.author_id
                ),
                content=mbody,
                email_to_all=email_to_lst,
                email_to_recipients=group["email_to_recipients"] or None,
                email_values=email_values,
                fields_values=message_info.get("mail_mail_values"),
                mail_message=message,
            )
        else:
            for partner in partners:
                self.assertSentEmail(
                    message.author_id or message.email_from,
                    partner,
                    **email_values,
                )
            if email_to_lst:
                self.assertSentEmail(
                    message.author_id or message.email_from,
                    email_to_lst,
                    **email_values,
                )

    def assertMailNotifications(self, messages, recipients_info, bus_notif_count=1):
        notifications, email_addrs, debug_info = self._find_expected_notifications(
            messages, recipients_info
        )
        done_msgs = self.env["mail.message"].sudo()
        done_notifs = self.env["mail.notification"].sudo()

        for message_info in recipients_info:
            extra_keys = set(message_info.keys()) - {
                "content",
                "email_to_recipients",
                "email_values",
                "mail_mail_values",
                "message_type",
                "message_values",
                "notif",
                "subtype",
            }
            if extra_keys:
                raise ValueError(f"Unsupported values: {extra_keys}")

            mbody, mtype = (
                message_info.get("content", ""),
                message_info.get("message_type", "comment"),
            )
            message_values = message_info.get("message_values", {})
            msubtype = message_info.get("message_values", {}).get(
                "subtype_id",
                self.env.ref(message_info.get("subtype", "mail.mt_comment")),
            )

            message, debug_info = self._find_notified_message(
                messages, mbody, mtype, msubtype
            )
            self.assertTrue(
                message,
                "Mail: not found message (content: %s, message_type: %s, subtype: %s\n%s)"
                % (mbody, mtype, msubtype and msubtype.name, debug_info),
            )

            if message_values:
                self.assertMessageFields(message, message_values)

            email_groups = {}
            status_groups = {
                "exception": {"email_lst": [], "partners": []},
                "outgoing": {"email_lst": [], "partners": []},
            }
            self.assertEqual(len(message.notification_ids), len(message_info["notif"]))
            for recipient in message_info["notif"]:
                done_notifs |= self._assert_recipient_notif(
                    message,
                    recipient,
                    notifications,
                    email_groups,
                    status_groups,
                    debug_info,
                )
            done_msgs |= message

            bus_notifications = (
                message.notification_ids._filtered_for_web_client().filtered(
                    lambda n: n.notification_status == "exception"
                )
            )
            if bus_notifications:
                self.assertMessageBusNotifications(message, bus_notif_count)

            email_values = {
                "body_content": mbody,
                "email_from": message.email_from,
                "references_content": [message.message_id],
            }
            if message_info.get("email_values"):
                email_values.update(message_info["email_values"])
            for group in email_groups.values():
                self._assert_notif_email_group(
                    message, message_info, group, status_groups, email_values, mbody
                )

            if not any(p for recipients in email_groups.values() for p in recipients):
                self.assertNoMail(
                    self.env["res.partner"],
                    email_to=email_addrs,
                    mail_message=message,
                    author=message.author_id,
                )

        return done_msgs, done_notifs

    def assertMessageBusNotifications(self, message, count=1):
        store = Store()
        message._message_notifications_to_store(store)
        self.assertBusNotifications(
            [(self.cr.dbname, "res.partner", message.author_id.id)] * count,
            [{"type": "mail.record/insert", "payload": store.get_result()}],
            check_unique=False,
        )

    def assertBusNotifications(self, channels, message_items=None, check_unique=True):
        self.env.cr.precommit.run()
        bus_notifs = (
            self.env["bus.bus"]
            .sudo()
            .search([("channel", "in", [json_dump(channel) for channel in channels])])
        )
        new_lines = "\n\n"

        def notif_to_string(notif):
            return f"{notif.channel}\n{notif.message}"

        self.assertEqual(
            bus_notifs.mapped("channel"),
            [json_dump(channel) for channel in channels],
            f"\n\nExpected:\n{new_lines[0].join([json_dump(channel) for channel in channels])}"
            f"\n\nReturned:\n{new_lines.join([notif_to_string(notif) for notif in bus_notifs])}",
        )
        for expected in message_items or []:
            for notification in bus_notifs:
                if json.loads(json_dump(expected)) == json.loads(notification.message):
                    break
            else:
                matching_notifs = [
                    n
                    for n in bus_notifs
                    if json.loads(n.message).get("type") == expected.get("type")
                ]
                if len(matching_notifs) == 1:
                    self.assertEqual(expected, json.loads(matching_notifs[0].message))
                if not matching_notifs:
                    matching_notifs = bus_notifs
                raise AssertionError(
                    "No notification was found with the expected value.\n\n"
                    f"Expected:\n{json_dump(expected)}\n\n"
                    f"Returned:\n{new_lines.join([notif_to_string(notif) for notif in matching_notifs])}"
                )
        if check_unique:
            self.assertEqual(len(bus_notifs), len(channels))
        return bus_notifs

    @contextmanager
    def assertBusNotificationType(self, expected_pairs):
        try:
            with self.mock_bus():
                yield
        finally:
            bus_notifs = (
                self.env["bus.bus"]
                .sudo()
                .search(
                    [
                        (
                            "channel",
                            "in",
                            [json_dump(channel) for channel, _ in expected_pairs],
                        )
                    ]
                )
            )
            notif_types = [
                (json.loads(notif.message).get("type"), notif.channel)
                for notif in bus_notifs
            ]
            expected_notif_types = [
                (notif_type, json_dump(channel))
                for channel, notif_type in expected_pairs
            ]
            self.assertEqual(notif_types, expected_notif_types)

    def assertNotified(self, message, recipients_info, is_complete=False):
        notifications = self._new_notifs.filtered(
            lambda notif: notif in message.notification_ids
        )
        if is_complete:
            self.assertEqual(len(notifications), len(recipients_info))
        for rinfo in recipients_info:
            recipient_notif = next(
                (
                    notif
                    for notif in notifications
                    if notif.res_partner_id == rinfo["partner"]
                ),
                False,
            )
            self.assertTrue(recipient_notif)
            self.assertEqual(recipient_notif.is_read, rinfo["is_read"])
            self.assertEqual(recipient_notif.notification_type, rinfo["type"])


class MailCommon(MailCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = cls.env.ref("base.user_admin")
        cls.partner_admin = cls.env.ref("base.partner_admin")
        cls.company_admin = cls.user_admin.company_id
        cls.company_admin.write(
            {
                "country_id": cls.env.ref("base.be").id,
                "email": "your.company@example.com",
                "name": "YourTestCompany",
            }
        )
        with patch.object(
            ResUsers,
            "_notify_security_setting_update",
            side_effect=lambda *args, **kwargs: None,
        ):
            cls.user_admin.write(
                {
                    "country_id": cls.env.ref("base.be").id,
                    "email": "test.admin@test.example.com",
                    "name": "Mitchell Admin",
                    "notification_type": "inbox",
                    "phone_ids": [
                        Command.create({"number": "0455135790", "type": "landline"})
                    ],
                }
            )
        cls.user_root = cls.env.ref("base.user_root")
        cls.partner_root = cls.user_root.partner_id
        cls.user_public = cls.env.ref("base.public_user")

        cls._activate_multi_company()

        cls._init_mail_gateway()
        cls._init_mail_servers()

        cls.env["ir.config_parameter"].set_param(
            "mail.restrict.template.rendering", False
        )

        cls.user_employee = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref("base.be").id,
            groups="base.group_user,base.group_partner_manager",
            login="employee",
            name="Ernest Employee",
            notification_type="inbox",
            signature="--\nErnest",
        )
        cls.partner_employee = cls.user_employee.partner_id
        cls.guest = cls.env["mail.guest"].create({"name": "Guest Mario"})

    @classmethod
    def _activate_multi_company(cls):
        cls._mc_enabled = True

        cls.company_2 = cls.env["res.company"].create(
            {
                "country_id": cls.env.ref("base.ca").id,
                "currency_id": cls.env.ref("base.CAD").id,
                "email": "company_2@test.example.com",
                "name": "Company 2",
            }
        )
        cls.company_3 = cls.env["res.company"].create(
            {
                "country_id": cls.env.ref("base.be").id,
                "currency_id": cls.env.ref("base.EUR").id,
                "email": "company_3@test.example.com",
                "name": "Company 3",
            }
        )
        cls.user_admin.write(
            {
                "company_ids": [
                    (4, cls.company_2.id),
                    (4, cls.company_3.id),
                ],
            }
        )

        cls.user_employee_c2 = mail_new_test_user(
            cls.env,
            login="employee_c2",
            groups="base.group_user,base.group_partner_manager",
            company_id=cls.company_2.id,
            company_ids=[(4, cls.company_2.id)],
            email="enguerrand@example.com",
            name="Enguerrand Employee C2",
            notification_type="inbox",
            signature="--\nEnguerrand",
        )
        cls.user_employee_c3 = mail_new_test_user(
            cls.env,
            login="employee_c3",
            company_id=cls.company_3.id,
            company_ids=[(4, cls.company_3.id)],
            email="freudenbergerg@example.com",
            groups="base.group_user,base.group_partner_manager",
            name="Freudenbergerg Employee C3",
            notification_type="inbox",
        )
        cls.partner_employee_c2 = cls.user_employee_c2.partner_id
        cls.partner_employee_c3 = cls.user_employee_c3.partner_id

        cls.user_erp_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company_2.id,
            company_ids=[(6, 0, (cls.company_admin + cls.company_2).ids)],
            email="etchenne@example.com",
            groups="base.group_user,base.group_erp_manager,mail.group_mail_template_editor,base.group_partner_manager",
            login="erp_manager",
            name="Etchenne Tchagada",
            notification_type="inbox",
            signature="--\nEtchenne",
        )

    @classmethod
    def _activate_multi_lang(
        cls,
        lang_code="es_ES",
        layout_arch_db=None,
        test_record=False,
        test_template=False,
    ):
        cls.env["res.lang"]._activate_lang(lang_code)
        with mute_logger("odoo.addons.base.models.ir_module", "odoo.tools.translate"):
            cls.env.ref("base.module_base")._update_translations([lang_code])
            cls.env.ref("base.module_mail")._update_translations([lang_code])
            cls.env.ref("base.module_test_mail")._update_translations([lang_code])
            code_translations.get_python_translations("mail", lang_code)
            code_translations.get_python_translations("test_mail", lang_code)

        if test_record:
            cls.env["ir.model"]._get(test_record._name).with_context(
                lang=lang_code
            ).name = "Spanish Model Description"

        code_translations.python_translations[("mail", "es_ES")] = {
            **code_translations.python_translations[("mail", "es_ES")],
            "View %s": "SpanishView %s",
        }
        cls.addClassCleanup(code_translations.python_translations.clear)

        if test_template:
            test_template.with_context(
                lang=lang_code
            ).subject = "SpanishSubject for {{ object.name }}"
            test_template.with_context(
                lang=lang_code
            ).body_html = '<p>SpanishBody for <t t-out="object.name" /></p>'

        if not layout_arch_db:
            layout_arch_db = """
<body>
    <t t-set="show_header" t-value="email_notification_force_header or (
        email_notification_allow_header and has_button_access)"/>
    <t t-set="show_footer" t-value="email_notification_force_footer or (
        email_notification_allow_footer and show_header and author_user and author_user._is_internal())"/>
    <p>English Layout for <t t-esc="model_description"/></p>
    <img t-att-src="'/logo.png?company=%s' % (company.id or 0)" t-att-alt="'%s' % company.name"/>
    <div t-if="show_header">HEADER
        <a t-if="has_button_access" t-att-href="button_access['url']">
            <t t-esc="button_access['title']"/>
        </a>
        <t t-if="actions" t-foreach="actions" t-as="action">
            <a t-att-href="action['url']">
                <t t-esc="action['title']"/>
            </a>
        </t>
    </div>
    <t t-out="message.body"/>
    <ul t-if="tracking_values">
        <li t-foreach="tracking_values" t-as="tracking">
            <t t-esc="tracking[0]"/>: <t t-esc="tracking[1]"/> -&gt; <t t-esc="tracking[2]"/>
        </li>
    </ul>
    <div t-if="signature" t-out="signature"/>
    <div t-if="show_footer">
        <p>Sent by <t t-esc="company.name"/></p>
        <span t-if="show_unfollow" id="mail_unfollow">
            | <a href="/mail/unfollow" style="text-decoration:none; color:#555555;">Unfollow</a>
        </span>
    </div>
</body>"""
        view = cls.env["ir.ui.view"].create(
            {
                "arch_db": layout_arch_db,
                "key": "test_layout",
                "name": "test_layout",
                "type": "qweb",
            }
        )
        cls.env["ir.model.data"].create(
            {
                "model": "ir.ui.view",
                "module": "mail",
                "name": "test_layout",
                "res_id": view.id,
            }
        )
        view.update_field_translations(
            "arch_db", {lang_code: {"English Layout for": "Spanish Layout para"}}
        )

    def _filter_channels_fields(self, /, *channels_data):
        ai_livechat_installed = (
            self.env["ir.module.module"]._get("ai_livechat").state == "installed"
        )
        for data in channels_data:
            if "ai.agent" not in self.env or (
                data.get("channel_type") == "livechat" and not ai_livechat_installed
            ):
                data.pop("ai_agent_id", None)
        return list(channels_data)

    def _filter_messages_fields(self, /, *messages_data):
        if "rating.rating" not in self.env:
            for data in messages_data:
                data.pop("rating_id", None)
        return list(messages_data)

    def _filter_partners_fields(self, /, *partners_data):
        return list(partners_data)

    def _filter_users_fields(self, /, *users_data):
        for data in users_data:
            if "hr.leave" not in self.env:
                data.pop("leave_date_to", None)
                data.pop("employee_ids", None)
        return list(users_data)

    def _filter_threads_fields(self, /, *threads_data):
        for data in threads_data:
            if (
                "mixin.rating" not in self.env.registry
                or data["model"] not in self.env.registry
                or not issubclass(
                    self.env.registry[data["model"]], self.env.registry["mixin.rating"]
                )
            ):
                data.pop("rating_avg", None)
                data.pop("rating_count", None)
        return list(threads_data)

    @classmethod
    def _setup_push_devices_for_partners(cls, partners, endpoint=None):
        endpoint = endpoint or "https://test.odoo.com/webpush/user"
        cls.vapid_public_key = cls.env[
            "mail.push.device"
        ].get_or_create_web_push_vapid_public_key()
        return (
            cls.env["mail.push.device"]
            .sudo()
            .create(
                [
                    {
                        "endpoint": f"{endpoint}/{partner.name}",
                        "expiration_time": None,
                        "keys": json.dumps(
                            {
                                "p256dh": "BGbhnoP_91U7oR59BaaSx0JnDv2oEooYnJRV2AbY5TBeKGCRCf0HcIJ9bOKchUCDH4cHYWo9SYDz3U-8vSxPL_A",
                                "auth": "DJFdtAgZwrT6yYkUMgUqow",
                            }
                        ),
                        "partner_id": partner.id,
                    }
                    for partner in partners
                ]
            )
        )


@contextlib.contextmanager
def freeze_all_time(dt=None):
    if not dt:
        dt = fields.Datetime.now()
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    with patch("odoo.db.BaseCursor.now", return_value=dt), freeze_time(dt):
        yield
