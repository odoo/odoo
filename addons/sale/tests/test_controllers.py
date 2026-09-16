import logging
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from markupsafe import Markup

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, JsonRpcException, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.portal.utils import get_portal_partner
from odoo.addons.sale.tests.common import SaleCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestPortalShareEmails(SaleCommon, MockEmail):
    def _share_wizard(self, partners):
        return self.env["portal.share"].create(
            {
                "res_model": self.sale_order._name,
                "res_id": self.sale_order.id,
                "partner_ids": [Command.set(partners.ids)],
            }
        )

    def test_share_description_uses_the_recipient_language(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.env["ir.module.module"]._load_module_terms(["portal"], ["fr_FR"])
        self.env["ir.model"]._get("sale.order").with_context(
            lang="fr_FR"
        ).name = "Commande destinataire"
        recipient = self.partner.copy(
            {"lang": "fr_FR", "email": "recipient@example.com"}
        )
        fallback_recipient = self.partner.copy(
            {"lang": False, "email": "fallback@example.com"}
        )
        wizard = self._share_wizard(recipient | fallback_recipient).with_context(
            lang="en_US"
        )
        with self.mock_mail_gateway():
            wizard._send_public_link()
        invitations = self.env["mail.message"].search(
            [
                ("model", "=", self.sale_order._name),
                ("res_id", "=", self.sale_order.id),
                ("message_type", "=", "user_notification"),
            ]
        )
        messages = invitations.filtered(
            lambda message: recipient in message.partner_ids
        )
        self.assertEqual(len(messages), 1)
        _logger.debug("Recipient-language share message: %s", messages.body)
        self.assertIn("commande destinataire", messages.body)
        self.assertEqual(
            messages.subject, f"Invitation pour accéder {self.sale_order.display_name}"
        )
        self.assertEqual(messages.partner_ids, recipient)
        fallback_message = invitations.filtered(
            lambda message: fallback_recipient in message.partner_ids
        )
        self.assertEqual(len(fallback_message), 1)
        self.assertNotIn("commande destinataire", fallback_message.body)
        self.assertEqual(
            fallback_message.subject,
            f"Invitation to access {self.sale_order.display_name}",
        )

    def test_signup_links_remain_valid_for_open_and_invitation_only_signup(self):
        for scope in ("b2c", "b2b"):
            with self.subTest(scope=scope):
                self.env["ir.config_parameter"].sudo().set_param(
                    "auth_signup.invitation_scope", scope
                )
                recipient = self.partner.copy({"email": f"signup-{scope}@example.com"})
                wizard = self._share_wizard(recipient)
                with (
                    self.mock_mail_gateway(),
                    patch.object(type(wizard), "_notify_share_invitation") as notify,
                ):
                    wizard._send_signup_link(recipient.with_context(signup_valid=True))
                notify.assert_called_once()
                url = urlsplit(notify.call_args.args[1])
                query = parse_qs(url.query)
                _logger.debug(
                    "Signup share scope=%s path=%s query keys=%s",
                    scope,
                    url.path,
                    sorted(query),
                )
                self.assertEqual(url.path, "/web/signup")
                resolved = self.env["res.partner"]._get_signup_partner(
                    query["token"][0], check_validity=True
                )
                self.assertEqual(resolved, recipient)
                redirect = urlsplit(query["redirect"][0])
                self.assertEqual(redirect.path, "/mail/view")
                self.assertEqual(
                    parse_qs(redirect.query),
                    {"model": ["sale.order"], "res_id": [str(self.sale_order.id)]},
                )

    def test_public_link_preparation_has_bounded_queries(self):
        recipients = self.env["res.partner"].create(
            [
                {
                    "name": f"Share recipient {index}",
                    "email": f"share-{index}@example.com",
                }
                for index in range(20)
            ]
        )
        wizard = self._share_wizard(recipients)
        # Isolate link preparation from the intentionally per-recipient mail delivery.
        with patch.object(type(wizard), "_notify_share_invitation") as post:
            wizard._send_public_link(recipients)
            costs = []
            for batch in (recipients[:2], recipients):
                self.env.flush_all()
                self.env.invalidate_all()
                post.reset_mock()
                before = self.env.cr.sql_statement_count
                wizard._send_public_link(batch)
                costs.append(self.env.cr.sql_statement_count - before)
                self.assertEqual(post.call_count, len(batch))
                for recipient, call in zip(batch, post.call_args_list, strict=True):
                    query = parse_qs(urlsplit(call.args[1]).query)
                    self.assertEqual(query["pid"], [str(recipient.id)])
                    self.assertEqual(
                        query["hash"], [self.sale_order._sign_token(recipient.id)]
                    )
            _logger.debug("Share link preparation SQL for 2/20 recipients: %s", costs)
            self.assertLessEqual(costs[1], costs[0] + 2)


@tagged("post_install", "-at_install")
class TestPortalDocumentLinks(HttpCase, SaleCommon):
    def test_valid_posting_identities_survive_recipient_validation(self):
        recipient = self.env["res.partner"].create(
            {"name": "Live signed recipient", "email": "signed@example.com"}
        )
        self.sale_order._portal_get_or_create_token()
        credentials = {
            "hash": self.sale_order._sign_token(recipient.id),
            "pid": recipient.id,
        }
        self.authenticate(None, None)
        cases = [
            (credentials, recipient),
            ({"token": self.sale_order.access_token}, self.sale_order.partner_id),
        ]
        for access, expected_author in cases:
            with self.subTest(credential_keys=sorted(access)):
                result = self.call_jsonrpc(
                    "/mail/message/post",
                    {
                        "thread_model": "sale.order",
                        "thread_id": self.sale_order.id,
                        "post_data": {"body": "Valid author control"},
                        **access,
                    },
                )
                message = self.env["mail.message"].browse(result["message_id"])
                _logger.debug(
                    "Valid portal posting keys=%s author=%s",
                    sorted(access),
                    message.author_id.id,
                )
                self.assertEqual(message.author_id, expected_author)
        recipient.unlink()
        reader = new_test_user(
            self.env,
            "deleted_recipient_logged_reader",
            groups="base.group_portal",
            partner_id=self.partner.id,
        )
        self.authenticate(reader.login, reader.login)
        result = self.call_jsonrpc(
            "/mail/message/post",
            {
                "thread_model": "sale.order",
                "thread_id": self.sale_order.id,
                "post_data": {"body": "Logged-in author has independent access"},
                **credentials,
            },
        )
        self.assertEqual(
            self.env["mail.message"].browse(result["message_id"]).author_id,
            reader.partner_id,
        )

    def test_deleted_recipient_cannot_post_as_the_public_user(self):
        recipient = self.env["res.partner"].create(
            {"name": "Deleted posting recipient"}
        )
        self.sale_order._portal_get_or_create_token()
        credentials = {
            "hash": self.sale_order._sign_token(recipient.id),
            "pid": recipient.id,
        }
        recipient.unlink()
        self.authenticate(None, None)
        domain = [("model", "=", "sale.order"), ("res_id", "=", self.sale_order.id)]
        before = self.env["mail.message"].search_count(domain)
        response = self.url_open(
            "/mail/message/post",
            json={
                "params": {
                    "thread_model": "sale.order",
                    "thread_id": self.sale_order.id,
                    "post_data": {
                        "body": "A deleted recipient must not gain a fallback identity"
                    },
                    **credentials,
                }
            },
        ).json()
        after = self.env["mail.message"].search_count(domain)
        _logger.debug(
            "Deleted-recipient post response: %s; created messages=%s",
            response,
            after - before,
        )
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], 404)
        self.assertEqual(after, before)

    def test_rating_chatter_page_keeps_only_readable_linked_references(self):
        reader = new_test_user(
            self.env,
            "rating_chatter_reader",
            groups="base.group_portal",
            partner_id=self.partner.id,
        )
        common_values = {
            "model": "sale.order",
            "res_id": self.sale_order.id,
            "message_type": "comment",
            "subtype_id": self.env.ref("mail.mt_comment").id,
        }
        linked, hidden = self.env["mail.message"].create(
            [
                {**common_values, "body": "Readable linked message"},
                {
                    **common_values,
                    "body": "Internal linked message",
                    "is_internal": True,
                },
            ]
        )
        source = self.env["mail.message"].create(
            {
                **common_values,
                "body": Markup(
                    '<a class="o_message_redirect" data-oe-model="mail.message" data-oe-id="%s">Readable</a><a class="o_message_redirect" data-oe-model="mail.message" data-oe-id="%s">Internal</a>'
                )
                % (linked.id, hidden.id),
            }
        )
        self.authenticate(reader.login, reader.login)
        result = self.call_jsonrpc(
            "/mail/chatter_fetch",
            {
                "thread_model": "sale.order",
                "thread_id": self.sale_order.id,
                "rating_include": True,
                "fetch_params": {"limit": 1},
            },
        )
        returned_ids = {value["id"] for value in result["data"]["mail.message"]}
        _logger.debug(
            "Rating chatter page=%s reference ids=%s",
            result["messages"],
            sorted(returned_ids),
        )
        self.assertEqual(result["messages"], source.ids)
        self.assertEqual(returned_ids, {source.id, linked.id})

    def test_deleted_share_recipient_is_not_resolved_as_an_author(self):
        recipient = self.env["res.partner"].create({"name": "Removed share recipient"})
        self.sale_order._portal_get_or_create_token()
        pid, signature = recipient.id, self.sale_order._sign_token(recipient.id)
        recipient.unlink()
        resolved = get_portal_partner(self.sale_order, signature, pid, None)
        _logger.debug("Deleted recipient resolution: ids=%s", resolved.ids)
        self.assertFalse(resolved)

    def test_chatter_init_after_share_recipient_deletion(self):
        recipient = self.env["res.partner"].create({"name": "Chatter share recipient"})
        message = self.env["mail.message"].create(
            {
                "model": "sale.order",
                "res_id": self.sale_order.id,
                "body": "Reaction target",
                "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_comment").id,
            }
        )
        self.sale_order._portal_get_or_create_token()
        credentials = {
            "hash": self.sale_order._sign_token(recipient.id),
            "pid": recipient.id,
        }
        self.authenticate(None, None)
        for deleted in (False, True):
            with self.subTest(deleted=deleted):
                if deleted:
                    recipient.unlink()
                result = self.call_jsonrpc(
                    "/portal/chatter_init",
                    {
                        "thread_model": "sale.order",
                        "thread_id": self.sale_order.id,
                        **credentials,
                    },
                )
                thread = next(
                    value
                    for value in result["mixin.mail.thread"]
                    if value["id"] == self.sale_order.id
                )
                _logger.debug(
                    "Share recipient deleted=%s chatter thread=%s", deleted, thread
                )
                self.assertEqual(thread["can_react"], not deleted)
                self.assertEqual(bool(thread.get("portal_partner")), not deleted)
                reaction_params = {
                    "message_id": message.id,
                    "content": "👍",
                    "action": "add",
                    **credentials,
                }
                if deleted:
                    with self.assertRaises(JsonRpcException) as error:
                        self.call_jsonrpc("/mail/message/reaction", reaction_params)
                    self.assertEqual(error.exception.code, 404)
                else:
                    self.call_jsonrpc("/mail/message/reaction", reaction_params)
                    self.assertEqual(message.reaction_ids.partner_id, recipient)

    def test_share_redirect_preserves_recipient_credentials(self):
        self.authenticate(None, None)
        share_url = self.sale_order._get_share_url(redirect=True, pid=self.partner.id)
        response = self.url_open(share_url, allow_redirects=False)
        self.assertEqual(response.status_code, 303)
        location = response.headers["Location"]
        query = parse_qs(urlsplit(location).query)
        _logger.debug(
            "Share redirect path=%s query keys=%s",
            urlsplit(location).path,
            sorted(query),
        )
        self.assertEqual(query["pid"], [str(self.partner.id)])
        self.assertEqual(query["hash"], [self.sale_order._sign_token(self.partner.id)])
        self.assertEqual(query["access_token"], [self.sale_order.access_token])
        self.assertEqual(
            self.url_open(location, allow_redirects=False).status_code, 200
        )

    def test_query_string_prefixes_preserve_token_and_http_access(self):
        self.authenticate(None, None)
        for prefix in ("", "&", "?"):
            with self.subTest(prefix=prefix):
                url = self.sale_order.get_portal_url(
                    query_string=f"{prefix}project_sharing=1&tag=a&tag=b&empty="
                )
                query = parse_qs(urlsplit(url).query, keep_blank_values=True)
                _logger.debug(
                    "Portal link query keys=%s prefix=%r", sorted(query), prefix
                )
                self.assertEqual(query["access_token"], [self.sale_order.access_token])
                self.assertEqual(query["project_sharing"], ["1"])
                self.assertEqual(query["tag"], ["a", "b"])
                self.assertEqual(query["empty"], [""])
                response = self.url_open(url, allow_redirects=False)
                self.assertEqual(response.status_code, 200)

    def test_portal_url_preserves_components_and_replaces_stale_token(self):
        self.sale_order.access_url = (
            f"/my/orders/{self.sale_order.id}?tag=a&tag=b&access_token=old#old"
        )
        url = urlsplit(
            self.sale_order.get_portal_url(
                suffix="/transaction",
                report_type="pdf",
                download=True,
                query_string="?note=A%26B&access_token=spoof",
                anchor="payment",
            )
        )
        self.assertEqual(url.path, f"/my/orders/{self.sale_order.id}/transaction")
        self.assertEqual(url.fragment, "payment")
        query = parse_qs(url.query)
        self.assertEqual(query["access_token"], [self.sale_order.access_token])
        self.assertEqual(query["tag"], ["a", "b"])
        self.assertEqual(query["note"], ["A&B"])
        self.assertEqual(query["report_type"], ["pdf"])
        self.assertEqual(query["download"], ["true"])

    def test_share_url_preserves_query_and_fragment(self):
        self.sale_order.access_url = (
            f"/my/orders/{self.sale_order.id}?tag=a&tag=b#details"
        )
        url = urlsplit(self.sale_order._get_share_url(pid=self.partner.id))
        query = parse_qs(url.query)
        self.assertEqual(url.fragment, "details")
        self.assertEqual(query["tag"], ["a", "b"])
        self.assertEqual(query["pid"], [str(self.partner.id)])
        self.assertEqual(query["hash"], [self.sale_order._sign_token(self.partner.id)])
        self.assertEqual(query["access_token"], [self.sale_order.access_token])

    def test_share_without_token_keeps_url_and_does_not_mint_token(self):
        self.sale_order.access_token = False
        self.sale_order.access_url = "/my/example?label=a%20b#details"
        self.assertEqual(
            self.sale_order._get_share_url(share_token=False),
            self.sale_order.access_url,
        )
        self.assertFalse(self.sale_order.access_token)

    def test_deleted_share_target_has_empty_fields_and_refuses_sending(self):
        wizard = self.env["portal.share"].create(
            {
                "res_model": "sale.order",
                "res_id": self.sale_order.id,
                "partner_ids": [Command.set(self.partner.ids)],
            }
        )
        self.sale_order.unlink()
        values = wizard.read(["resource_ref", "share_link", "access_warning"])[0]
        _logger.debug("Deleted share target fields: %s", values)
        for name in ("resource_ref", "share_link", "access_warning"):
            self.assertFalse(values[name])
        with self.assertRaisesRegex(UserError, "no portal page"):
            wizard.action_send_mail()

    def test_shared_record_checks_target_access(self):
        operator = new_test_user(
            self.env,
            "share_contact_manager",
            groups="base.group_user,base.group_partner_manager",
        )
        self.assertFalse(self.sale_order.with_user(operator).has_access("read"))
        wizard = (
            self.env["portal.share"]
            .with_user(operator)
            .create(
                {
                    "res_model": "sale.order",
                    "res_id": self.sale_order.id,
                    "partner_ids": [Command.set(self.partner.ids)],
                }
            )
        )
        with self.assertRaises(AccessError):
            wizard._get_shared_record()


@tagged("post_install", "-at_install")
class TestAccessRightsControllers(HttpCase, SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls._create_new_portal_user()

    @mute_logger("odoo.addons.base.models.ir_model", "odoo.addons.base.models.ir_rule")
    def test_access_controller(self):
        private_so = self.sale_order
        portal_so = self.sale_order.copy()
        portal_so.partner_id = self.user_portal.partner_id.id

        portal_so._portal_get_or_create_token()
        token = portal_so.access_token

        self.authenticate(None, None)

        req = self.url_open(
            url="/my/orders/%s?report_type=pdf" % portal_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)

        req = self.url_open(
            url="/my/orders/%s?access_token=%s&report_type=pdf"
            % (
                portal_so.id,
                "foo",
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)

        req = self.url_open(
            url="/my/orders/%s?access_token=%s&report_type=pdf"
            % (
                portal_so.id,
                token,
            ),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)

        self.authenticate(self.user_portal.login, self.user_portal.login)

        req = self.url_open(
            url="/my/orders/%s?report_type=pdf" % portal_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)

        req = self.url_open(
            url="/my/orders/%s?report_type=pdf" % private_so.id,
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 303)


@tagged("post_install", "-at_install")
class TestSalesControllers(HttpCase, SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_portal = cls._create_new_portal_user()

    def test_sales_portal_report(self):
        portal_so = self.sale_order.copy()
        portal_so.message_subscribe(self.user_portal.partner_id.ids)

        self.authenticate(None, None)

        req = self.url_open(
            portal_so.get_portal_url(report_type="pdf"), allow_redirects=False
        )
        self.assertEqual(req.status_code, 200)
        self.assertEqual(
            req.headers["content-disposition"],
            f"inline; filename*=UTF-8''Quotation_{portal_so.name}.pdf",
        )

        req = self.url_open(
            portal_so.get_portal_url(report_type="pdf", download=True),
            allow_redirects=False,
        )
        self.assertEqual(req.status_code, 200)
        self.assertEqual(
            req.headers["content-disposition"],
            f"attachment; filename*=UTF-8''Quotation_{portal_so.name}.pdf",
        )

    def _viewed_message_count(self, order):
        subtype = self.env.ref("sale.mt_order_viewed")
        return len(order.message_ids.filtered(lambda m: m.subtype_id == subtype))

    def test_viewed_note_only_posts_for_draft_orders(self):
        confirmed_so = self.sale_order.copy()
        confirmed_so.message_subscribe(self.user_portal.partner_id.ids)
        confirmed_so.action_confirm()
        self.assertEqual(confirmed_so.state, "done")

        self.authenticate(None, None)
        req = self.url_open(confirmed_so.get_portal_url(), allow_redirects=False)
        self.assertEqual(req.status_code, 200)
        self.assertEqual(
            self._viewed_message_count(confirmed_so),
            0,
            "a confirmed order must not get the customer-viewed note",
        )

        draft_so = self.sale_order.copy()
        draft_so.message_subscribe(self.user_portal.partner_id.ids)
        self.assertEqual(draft_so.state, "draft")

        req = self.url_open(draft_so.get_portal_url(), allow_redirects=False)
        self.assertEqual(req.status_code, 200)
        self.assertEqual(
            self._viewed_message_count(draft_so),
            1,
            "a draft order must still get the customer-viewed note",
        )

    def test_signature_acceptance_propagates_signature_context(self):
        self.sale_order.require_signature = True
        self.sale_order.require_payment = False
        self.sale_order._portal_get_or_create_token()

        seen_contexts = []
        original_confirm_order = type(self.sale_order)._confirm_order

        def _spy_confirm_order(recordset, *args, **kwargs):
            seen_contexts.append(dict(recordset.env.context))
            return original_confirm_order(recordset, *args, **kwargs)

        self.authenticate(None, None)
        with patch.object(type(self.sale_order), "_confirm_order", _spy_confirm_order):
            result = self.call_jsonrpc(
                f"/my/orders/{self.sale_order.id}/accept",
                {
                    "access_token": self.sale_order.access_token,
                    "name": "A Customer",
                    "signature": (
                        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4"
                        "2mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
                    ),
                },
                timeout=60,
            )

        self.assertNotIn("error", result or {})
        self.assertEqual(len(seen_contexts), 1)
        self.assertTrue(seen_contexts[0].get("sale_include_signature"))


@tagged("post_install", "-at_install", "mail_flow")
class TestSaleSignature(HttpCaseWithUserPortal):
    def test_01_portal_sale_signature_tour(self):
        portal_user_partner = self.partner_portal
        sales_order = self.env["sale.order"].create(
            {
                "name": "test SO",
                "partner_id": portal_user_partner.id,
                "sent": True,
                "require_payment": False,
            }
        )
        self.env["sale.order.line"].create(
            {
                "order_id": sales_order.id,
                "product_id": self.env["product.product"]
                .create({"name": "A product"})
                .id,
            }
        )
        self.assertFalse(sales_order.message_partner_ids)

        email_act = sales_order.action_send_quotation()
        email_ctx = email_act.get("context", {})
        sales_order.with_context(**email_ctx).message_post_with_source(
            self.env["mail.template"].browse(email_ctx.get("default_template_id")),
            subtype_xmlid="mail.mt_comment",
        )
        self.assertFalse(
            sales_order.message_partner_ids,
            "Do not automatically set customer as follower, will be suggested recipient",
        )

        self.start_tour("/", "sale_signature", login="portal")
