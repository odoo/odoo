import logging

from odoo.exceptions import UserError
from odoo.tests import HttpCase, TransactionCase, new_test_user, tagged

_logger = logging.getLogger(__name__)


@tagged("-at_install", "post_install")
class TestPortalShareRedirects(HttpCase):
    def test_invalid_targets_fall_back_for_visitors_and_portal_users(self):
        user = new_test_user(
            self.env, "share_redirect_reader", groups="base.group_portal"
        )
        for login in (None, user.login):
            self.authenticate(login, login)
            for model in (
                "mixin.portal",
                "mixin.mail.thread",
                "no.such.model",
                "res.partner",
            ):
                with self.subTest(login=login, model=model):
                    response = self.url_open(
                        "/mail/view",
                        params={"model": model, "res_id": 99999999},
                        allow_redirects=False,
                    )
                    _logger.debug(
                        "Share target fallback model=%s login=%s status=%s",
                        model,
                        login,
                        response.status_code,
                    )
                    self.assertEqual(response.status_code, 303)
                    if login:
                        self.assertEqual(response.headers["Location"], "/my")


@tagged("-at_install", "post_install")
class TestPortalShareTarget(TransactionCase):
    def test_abstract_portal_model_is_not_a_share_target(self):
        wizard = self._wizard_on("mixin.portal", 1)
        self.assertFalse(wizard._get_portal_record())
        self.assertFalse(wizard.resource_ref)
        with self.assertRaisesRegex(UserError, "no portal page"):
            wizard.action_send_mail()

    def test_default_get_only_returns_requested_fields(self):
        defaults = (
            self.env["portal.share"]
            .with_context(
                active_model="res.partner", active_id=self.non_portal_record.id
            )
            .default_get(["note"])
        )
        self.assertNotIn("res_model", defaults)
        self.assertNotIn("res_id", defaults)

    def test_explicit_defaults_take_priority_over_active_record(self):
        defaults = (
            self.env["portal.share"]
            .with_context(
                active_model="res.partner",
                active_id=self.non_portal_record.id,
                default_res_model="explicit.model",
                default_res_id=42,
            )
            .default_get(["res_model", "res_id"])
        )
        self.assertEqual(defaults, {"res_model": "explicit.model", "res_id": 42})

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.recipient = cls.env["res.partner"].create(
            {"name": "Share Recipient", "email": "share.recipient@example.com"}
        )
        cls.non_portal_record = cls.env["res.partner"].create({"name": "Share Target"})

    def _wizard_on(self, res_model, res_id):
        return self.env["portal.share"].create(
            {
                "res_model": res_model,
                "res_id": res_id,
                "partner_ids": [(6, 0, self.recipient.ids)],
            }
        )

    def test_reading_a_non_portal_target_does_not_raise(self):
        wizard = self._wizard_on("res.partner", self.non_portal_record.id)
        values = wizard.read(["resource_ref", "share_link", "access_warning"])[0]
        self.assertFalse(
            values["resource_ref"],
            "a model outside the mixin.portal hierarchy has no shareable "
            "reference, so the field must come back empty rather than raise",
        )
        self.assertFalse(values["share_link"])

    def test_unknown_model_does_not_raise(self):
        wizard = self._wizard_on("no.such.model", 1)
        values = wizard.read(["resource_ref", "share_link"])[0]
        self.assertFalse(values["resource_ref"])
        self.assertFalse(values["share_link"])

    def test_missing_res_id_does_not_raise(self):
        wizard = self._wizard_on("res.partner", 0)
        self.assertFalse(wizard.resource_ref)
        self.assertFalse(wizard.share_link)

    def test_sending_to_a_non_portal_target_is_refused_cleanly(self):
        wizard = self._wizard_on("res.partner", self.non_portal_record.id)
        messages_before = self.env["mail.message"].search_count([])
        with self.assertRaises(UserError):
            wizard.action_send_mail()
        self.assertEqual(
            self.env["mail.message"].search_count([]),
            messages_before,
            "no share mail may be posted for an unshareable target",
        )

    def test_default_get_from_a_non_portal_active_model(self):
        wizard = (
            self.env["portal.share"]
            .with_context(
                active_model="res.partner", active_id=self.non_portal_record.id
            )
            .create({"partner_ids": [(6, 0, self.recipient.ids)]})
        )
        self.assertEqual(wizard.res_model, "res.partner")
        self.assertFalse(wizard.read(["resource_ref"])[0]["resource_ref"])
