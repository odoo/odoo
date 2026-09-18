from unittest.mock import patch

import requests

from odoo.exceptions import ValidationError
from odoo.libs.webhook import (
    get_log_target,
    scrub_url,
)
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger

_MODULE = "odoo.addons.base.models.ir_actions_server"
_DELIVERY = "odoo.libs.webhook"
_SECRET = "T00000/B00000/xoxbSECRETTOKENvalue"
_URL = f"https://hooks.slack.com/services/{_SECRET}"


class WebhookCase(TransactionCase):
    webhook_url = "https://example.com/hook"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "webhook target"})
        cls.model = cls.env["ir.model"]._get("res.partner")

    def _action(self, **vals):
        return self.env["ir.actions.server"].create(
            {
                "name": "notify",
                "model_id": self.model.id,
                "state": "webhook",
                "webhook_url": self.webhook_url,
                **vals,
            }
        )

    def _run(self, action):
        action.with_context(active_id=self.partner.id, active_model="res.partner").run()
        self.env.cr.precommit.run()
        self.env.cr.postcommit.run()


@tagged("post_install", "-at_install")
class TestWebhookTimeout(WebhookCase):
    def test_the_default_is_the_historical_one_second(self):
        self.assertEqual(self._action().webhook_timeout, 1)

    def test_the_configured_timeout_reaches_the_request(self):
        action = self._action(webhook_timeout=12)
        with patch.object(requests.Session, "post") as post:
            self._run(action)
        self.assertEqual(post.call_args.kwargs["timeout"], 12)

    @mute_logger(_MODULE, _DELIVERY)
    def test_a_timeout_names_the_action_and_says_what_to_do(self):
        action = self._action()
        with (
            patch.object(
                requests.Session, "post", side_effect=requests.exceptions.ReadTimeout
            ),
            self.assertLogs(_DELIVERY, level="WARNING") as logs,
        ):
            self._run(action)

        message = "\n".join(logs.output)
        self.assertIn("notify", message, "the action must be identifiable")
        self.assertIn("example.com", message, "so must the receiver")
        self.assertIn("may or may not", message, "a timeout is genuinely ambiguous")

    @mute_logger(_MODULE, _DELIVERY)
    def test_a_refusal_is_an_error_and_says_it_will_not_retry(self):
        action = self._action()
        with (
            patch.object(
                requests.Session,
                "post",
                side_effect=requests.exceptions.ConnectionError("refused"),
            ),
            self.assertLogs(_DELIVERY, level="ERROR") as logs,
        ):
            self._run(action)

        message = "\n".join(logs.output)
        self.assertIn("notify", message)
        self.assertIn("NOT be retried", message)

    def test_the_ceiling_refuses_a_worker_holding_value(self):
        with self.assertRaises(ValidationError) as caught:
            self._action(webhook_timeout=600)
        self.assertIn("after the transaction commits", str(caught.exception))

    def test_zero_is_refused_rather_than_meaning_no_timeout(self):
        with self.assertRaises(ValidationError):
            self._action(webhook_timeout=0)

    def test_the_ceiling_only_binds_webhook_actions(self):
        action = self.env["ir.actions.server"].create(
            {
                "name": "not a webhook",
                "model_id": self.model.id,
                "state": "code",
                "code": "pass",
                "webhook_timeout": 0,
            }
        )
        self.assertEqual(action.state, "code")


@tagged("post_install", "-at_install")
class TestWebhookLogTarget(TransactionCase):
    def test_only_the_host_survives(self):
        self.assertEqual(get_log_target(_URL), "hooks.slack.com")

    def test_userinfo_and_port_do_not_survive(self):
        self.assertEqual(
            get_log_target("https://user:pw@example.com:8443/hook?token=abc"),
            "example.com",
        )

    def test_a_url_with_no_host_still_names_something(self):
        self.assertEqual(get_log_target("not a url"), "<unknown host>")

    def test_the_scrubber_removes_the_full_url(self):
        message = f"404 Client Error: Not Found for url: {_URL}"
        scrubbed = scrub_url(message, _URL, "hooks.slack.com")
        self.assertNotIn(_SECRET, scrubbed)
        self.assertIn("404 Client Error", scrubbed, "the useful half stays")

    def test_the_scrubber_removes_a_bare_path(self):
        message = (
            "HTTPSConnectionPool(host='hooks.slack.com', port=443): Max retries "
            f"exceeded with url: /services/{_SECRET} (Caused by NameResolutionError)"
        )
        scrubbed = scrub_url(message, _URL, "hooks.slack.com")
        self.assertNotIn(_SECRET, scrubbed)
        self.assertIn("Max retries exceeded", scrubbed)

    def test_the_scrubber_removes_a_query_token(self):
        url = "https://example.com/hook?token=abcd1234"
        scrubbed = scrub_url(f"failed for url: {url}", url, "example.com")
        self.assertNotIn("abcd1234", scrubbed)

    def test_a_root_path_is_not_substituted_into_the_sentence(self):
        url = "https://example.com/"
        message = "Max retries exceeded with url: / (Caused by x/y/z)"
        self.assertEqual(scrub_url(message, url, "example.com"), message)


@tagged("post_install", "-at_install")
class TestWebhookNeverLogsItsSecret(WebhookCase):
    webhook_url = _URL

    def _captured(self, side_effect=None, level="DEBUG"):
        action = self._action()
        with (
            patch.object(requests.Session, "post", side_effect=side_effect) as post,
            self.assertLogs(_MODULE, level=level) as scheduled,
            self.assertLogs(_DELIVERY, level=level) as delivered,
        ):
            if side_effect is None:
                post.return_value.raise_for_status.return_value = None
            self._run(action)
        return "\n".join(scheduled.output + delivered.output), post

    @mute_logger(_MODULE, _DELIVERY)
    def test_a_successful_call_logs_the_host_and_not_the_token(self):
        output, post = self._captured()

        self.assertNotIn(_SECRET, output, "the token reached the log")
        self.assertIn("hooks.slack.com", output)
        self.assertIn("notify", output, "the action is what identifies it now")
        self.assertEqual(
            # A MagicMock is not a descriptor, so patching the class attribute
            # with one leaves it unbound and the call arrives as mock(url, ...)
            # with no `self`. Where the replacement is a plain function it binds
            # and the url is args[1]; test_ir_actions.py does that instead.
            post.call_args.args[0],
            _URL,
            "the full URL must still reach requests -- only the log is trimmed",
        )

    @mute_logger(_MODULE, _DELIVERY)
    def test_a_timeout_logs_no_token(self):
        output, _post = self._captured(side_effect=requests.exceptions.ReadTimeout)
        self.assertNotIn(_SECRET, output)
        self.assertIn("may or may not", output)

    @mute_logger(_MODULE, _DELIVERY)
    def test_a_connection_error_logs_no_token(self):
        error = requests.exceptions.ConnectionError(
            "HTTPSConnectionPool(host='hooks.slack.com', port=443): Max retries "
            f"exceeded with url: /services/{_SECRET} (Caused by NameResolutionError)"
        )
        output, _post = self._captured(side_effect=error)

        self.assertNotIn(_SECRET, output)
        self.assertIn("NOT be retried", output)
        self.assertIn("Max retries exceeded", output, "the diagnosis is still readable")

    @mute_logger(_MODULE, _DELIVERY)
    def test_an_http_error_logs_no_token(self):
        response = requests.Response()
        response.status_code = 404
        response.url = _URL
        error = requests.exceptions.HTTPError(
            f"404 Client Error: Not Found for url: {_URL}", response=response
        )
        output, _post = self._captured(side_effect=error)

        self.assertNotIn(_SECRET, output)
        self.assertIn("404", output)

    @mute_logger(_MODULE, _DELIVERY)
    def test_a_rollback_logs_no_token(self):
        action = self._action()
        with (
            patch.object(requests.Session, "post") as post,
            self.assertLogs(_MODULE, level="WARNING") as logs,
        ):
            action.with_context(
                active_id=self.partner.id, active_model="res.partner"
            ).run()
            self.env.cr.postrollback.run()

        output = "\n".join(logs.output)
        self.assertNotIn(_SECRET, output)
        self.assertIn("rolled back", output)
        post.assert_not_called()


@tagged("post_install", "-at_install")
class TestWebhookPayloadBytes(WebhookCase):
    def test_bytes_are_sent_as_text_not_as_their_repr(self):
        action = self._action()
        dumped = action._dump_webhook_payload(
            {"text": b"ab", "array": bytearray(b"c"), "raw": b"\xff\xfe"}
        )
        self.assertEqual(dumped, '{"array":"c","raw":"//4=","text":"ab"}')
        self.assertNotIn("b'", dumped)
