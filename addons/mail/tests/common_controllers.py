import json

from markupsafe import Markup
from requests.exceptions import HTTPError

from odoo import fields
from odoo.addons.base.tests.common import HttpCase
from odoo.addons.mail.tests.common import mail_new_test_user, MailCommon
from odoo.http import Request
from odoo.tests import JsonRpcException
from odoo.tools import file_open, mute_logger


class MessagePostSubTestData:
    def __init__(self, user, allowed, /, *, partners=None, partner_emails=None, route_kw=None,
                 exp_author=None, exp_partners=None, exp_emails=None):
        self.user = user if user._name == "res.users" else user.env.ref("base.public_user")
        self.guest = user if user._name == "mail.guest" else user.env["mail.guest"]
        self.allowed = allowed
        self.route_kw = {
            "context": {"mail_post_autofollow_author_skip": True, "mail_post_autofollow": False},
            **(route_kw or {}),
        }
        if partner_emails is not None:
            self.route_kw["partner_emails"] = partner_emails
        self.post_data = {
            "body": "<p>Hello</p>",
            "message_type": "comment",
            "subtype_xmlid": "mail.mt_comment",
        }
        if partners is not None:
            self.post_data["partner_ids"] = partners.ids
        self.exp_author = exp_author
        self.exp_partners = exp_partners
        self.exp_emails = exp_emails


class MailControllerCommon(HttpCase, MailCommon):
    # Note that '_get_with_access' is going to call '_get_thread_with_access'
    # which relies on classic portal parameter given as kwargs on most routes
    # (aka hash, token, pid)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.maxDiff = None
        cls._create_portal_user()
        cls.guest = cls.env["mail.guest"].create({"name": "Guest"})
        last_message = cls.env["mail.message"].search([], order="id desc", limit=1)
        cls.fake_message = cls.env["mail.message"].browse(last_message.id + 1000000)
        cls.user_employee_nopartner = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            country_id=cls.env.ref('base.be').id,
            groups='base.group_user,mail.group_mail_template_editor',
            login='employee_nopartner',
            name='Elodie EmployeeNoPartner',
            notification_type='inbox',
        )
        # whatever default creation values, we need a "no partner manager" user
        cls.user_employee_nopartner.write({'groups_id': [(3, cls.env.ref('base.group_partner_manager').id)]})

    def _authenticate_pseudo_user(self, pseudo_user):
        user = pseudo_user if pseudo_user._name == "res.users" else self.user_public
        guest = pseudo_user if pseudo_user._name == "mail.guest" else self.env["mail.guest"]
        if user and user != self.user_public:
            self.authenticate(user.login, user.login)
        else:
            self.authenticate(None, None)
        if guest:
            self.opener.cookies[guest._cookie_name] = guest._format_auth_cookie()
        return user, guest

    def _get_sign_token_params(self, record):
        if 'access_token' not in record:
            raise ValueError("Test should run with portal installed")
        access_token = record._portal_ensure_token()
        partner = record.env["res.partner"].create({"name": "Sign Partner"})
        _hash = record._sign_token(partner.id)
        token = {"token": access_token}
        bad_token = {"token": "incorrect token"}
        sign = {"hash": _hash, "pid": partner.id}
        bad_sign = {"hash": "incorrect hash", "pid": partner.id}
        return token, bad_token, sign, bad_sign, partner


class MailControllerAttachmentCommon(MailControllerCommon):

    def _execute_subtests(self, document, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            user, guest = self._authenticate_pseudo_user(data_user)
            with self.subTest(document=document, user=user.name, guest=guest.name, route_kw=route_kw):
                if allowed:
                    attachment_id = self._upload_attachment(document, route_kw)
                    attachment = self.env["ir.attachment"].sudo().search([("id", "=", attachment_id)])
                    self.assertTrue(attachment)
                    self._delete_attachment(attachment, route_kw)
                    self.assertFalse(attachment.exists())
                else:
                    with self.assertRaises(
                        HTTPError, msg="upload attachment should raise NotFound"
                    ):
                        self._upload_attachment(document, route_kw)

    def _upload_attachment(self, document, route_kw):
        with mute_logger("odoo.http"), file_open("addons/web/__init__.py") as file:
            res = self.url_open(
                url="/mail/attachment/upload",
                data={
                    "csrf_token": Request.csrf_token(self),
                    "is_pending": True,
                    "thread_id": document.id,
                    "thread_model": document._name,
                    **route_kw,
                },
                files={"ufile": file},
            )
            res.raise_for_status()
            return json.loads(res.content.decode("utf-8"))["data"]["ir.attachment"][0]["id"]

    def _delete_attachment(self, attachment, route_kw):
        self.make_jsonrpc_request(
            route="/mail/attachment/delete",
            params={
                "attachment_id": attachment.id,
                "access_token": attachment.access_token,
                **route_kw,
            },
        )


class MailControllerBinaryCommon(MailControllerCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_2 = cls.env["mail.guest"].create({"name": "Guest 2"})

    def _execute_subtests(self, record, subtests):
        for data_user, allowed in subtests:
            user, guest = self._authenticate_pseudo_user(data_user)
            with self.subTest(user=user.name, guest=guest.name, record=record):
                if allowed:
                    self.assertEqual(
                        self._get_avatar_url(record).headers["Content-Disposition"],
                        f'inline; filename="{record.name}.svg"',
                    )
                else:
                    self.assertEqual(
                        self._get_avatar_url(record).headers["Content-Disposition"],
                        "inline; filename=placeholder.png",
                    )

    def _get_avatar_url(self, record):
        url = f"/web/image?field=avatar_128&id={record.id}&model={record._name}&unique={fields.Datetime.to_string(record.write_date)}"
        return self.url_open(url)

    def _post_message(self, document, auth_pseudo_user):
        _user, _guest = self._authenticate_pseudo_user(auth_pseudo_user)
        self.make_jsonrpc_request(
            route="/mail/message/post",
            params={
                "thread_model": document._name,
                "thread_id": document.id,
                "post_data": {
                    "body": "Test",
                    "message_type": "comment",
                    "subtype_xmlid": "mail.mt_comment",
                },
            },
        )


class MailControllerReactionCommon(MailControllerCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reaction = "😊"

    def _execute_subtests(self, message, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            kwargs = args[1] if len(args) > 1 else {}
            user, guest = self._authenticate_pseudo_user(data_user)
            with self.subTest(user=user.name, guest=guest.name, route_kw=route_kw):
                if allowed:
                    self._add_reaction(message, self.reaction, route_kw)
                    reactions = message.reaction_ids
                    self.assertEqual(len(reactions), 1)
                    expected_partner = kwargs.get("partner")
                    if guest and not expected_partner:
                        self.assertEqual(reactions.guest_id, guest)
                    else:
                        self.assertEqual(reactions.partner_id, expected_partner or user.partner_id)
                    self._remove_reaction(message, self.reaction, route_kw)
                    self.assertFalse(message.reaction_ids)
                else:
                    with self.assertRaises(
                        JsonRpcException, msg="add reaction should raise NotFound"
                    ):
                        self._add_reaction(message, self.reaction, route_kw)
                    with self.assertRaises(
                        JsonRpcException, msg="remove reaction should raise NotFound"
                    ):
                        self._remove_reaction(message, self.reaction, route_kw)

    def _add_reaction(self, message, content, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/reaction",
            params={"action": "add", "content": content, "message_id": message.id, **route_kw},
        )

    def _remove_reaction(self, message, content, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/reaction",
            params={"action": "remove", "content": content, "message_id": message.id, **route_kw},
        )


class MailControllerThreadCommon(MailControllerCommon):

    def _execute_message_post_subtests(self, record, tests: list[MessagePostSubTestData]):
        for test in tests:
            self._authenticate_pseudo_user(test.user if (test.user and test.user != self.user_public) else test.guest)
            with self.subTest(record=record, user=test.user.name, guest=test.guest.name, route_kw=test.route_kw):
                if test.allowed:
                    message = self._message_post(record, test.post_data, test.route_kw)
                    if test.guest and not test.exp_author:
                        self.assertEqual(message.author_guest_id, test.guest)
                    else:
                        self.assertEqual(message.author_id, test.exp_author or test.user.partner_id)
                    if test.exp_partners is not None:
                        self.assertEqual(message.partner_ids, test.exp_partners)
                    if test.exp_emails is not None:
                        self.assertEqual(message.partner_ids.mapped("email"), test.exp_emails)
                else:
                    with self.assertRaises(JsonRpcException, msg="werkzeug.exceptions.NotFound"):
                        self._message_post(record, test.post_data, test.route_kw)

    def _message_post(self, record, post_data, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/post",
            params={
                "thread_model": record._name,
                "thread_id": record.id,
                "post_data": post_data,
                **route_kw,
            },
        )
        return self.env["mail.message"].search(
            [("res_id", "=", record.id), ("model", "=", record._name)], order="id desc", limit=1
        )


class MailControllerUpdateCommon(MailControllerCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.message_body = "Message body"
        cls.alter_message_body = "Altered message body"

    def _execute_subtests(self, message, subtests):
        for data_user, allowed, *args in subtests:
            route_kw = args[0] if args else {}
            user, guest = self._authenticate_pseudo_user(data_user)
            with self.subTest(user=user.name, guest=guest.name, route_kw=route_kw):
                if allowed:
                    self._update_content(message.id, self.alter_message_body, route_kw)
                    self.assertEqual(message.body,
                                     Markup('<p>Altered message body<span class="o-mail-Message-edited"></span></p>'))
                else:
                    with self.assertRaises(
                        JsonRpcException,
                        msg="update message content should raise NotFound",
                    ):
                        self._update_content(message.id, self.alter_message_body, route_kw)

    def _update_content(self, message_id, body, route_kw):
        self.make_jsonrpc_request(
            route="/mail/message/update_content",
            params={
                "message_id": message_id,
                "body": body,
                "attachment_ids": [],
                **route_kw,
            },
        )
