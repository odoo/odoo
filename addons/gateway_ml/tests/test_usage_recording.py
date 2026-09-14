from unittest.mock import Mock, patch

from odoo.tests import TransactionCase, tagged

from odoo.addons.gateway_ml.tests.common import connect
from odoo.addons.gateway_ml.tools.ai_clients import get_ai_client
from odoo.addons.gateway_ml.tools.usage import (
    SpendCapReached,
    read_anthropic_messages,
    read_deepgram,
    read_gemini_native,
    read_openai_compatible,
)


@tagged("post_install", "-at_install")
class TestUsageReaders(TransactionCase):
    def test_openai_chat_usage_names_the_requested_model(self):
        usage = read_openai_compatible(
            "https://api.openai.com/v1/chat/completions",
            {"json": {"model": "gpt-5.6-luna"}},
            {
                "model": "gpt-5.6-luna-2026-08-01",
                "usage": {"prompt_tokens": 120, "completion_tokens": 30},
            },
        )
        self.assertEqual(
            usage,
            {
                "model": "gpt-5.6-luna",
                "input_tokens": 120,
                "output_tokens": 30,
                "audio_seconds": 0,
            },
        )

    def test_a_transcription_billed_by_duration_reads_seconds(self):
        usage = read_openai_compatible(
            "https://api.openai.com/v1/audio/transcriptions",
            {"data": {"model": "gpt-transcribe"}},
            {"text": "hola", "usage": {"type": "duration", "seconds": 42}},
        )
        self.assertEqual(
            (usage["model"], usage["audio_seconds"]), ("gpt-transcribe", 42)
        )

    def test_a_body_without_usage_reads_nothing(self):
        for reader in (read_openai_compatible, read_anthropic_messages):
            with self.subTest(reader=reader.__name__):
                self.assertIsNone(reader("", {}, "plain text"))
                self.assertIsNone(reader("", {}, {"choices": []}))

    def test_anthropic_counts_cached_input_as_input(self):
        usage = read_anthropic_messages(
            "",
            {"json": {"model": "claude-sonnet-5"}},
            {
                "usage": {
                    "input_tokens": 10,
                    "cache_creation_input_tokens": 5,
                    "cache_read_input_tokens": 100,
                    "output_tokens": 7,
                }
            },
        )
        self.assertEqual((usage["input_tokens"], usage["output_tokens"]), (115, 7))

    def test_gemini_reads_the_model_from_the_path_and_bills_thinking(self):
        usage = read_gemini_native(
            "https://generativelanguage.googleapis.com/v1beta/models/"
            "gemini-flash-lite-latest:generateContent",
            {"json": {}},
            {
                "usageMetadata": {
                    "promptTokenCount": 50,
                    "candidatesTokenCount": 20,
                    "thoughtsTokenCount": 5,
                }
            },
        )
        self.assertEqual(
            (usage["model"], usage["input_tokens"], usage["output_tokens"]),
            ("gemini-flash-lite-latest", 50, 25),
        )

    def test_deepgram_bills_the_duration(self):
        usage = read_deepgram(
            "", {"params": {"model": "nova-3"}}, {"metadata": {"duration": 12.5}}
        )
        self.assertEqual((usage["model"], usage["audio_seconds"]), ("nova-3", 12.5))
        self.assertIsNone(read_deepgram("", {}, {"metadata": {}}))


@tagged("post_install", "-at_install")
class TestUsageOnTheExchangeRow(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.openai = cls.env.ref("gateway_ml.ai_provider_openai")
        connect(cls.env, cls.openai)
        cls.model = cls.openai._service_for("chat").model_id
        cls.model.write({"cost_per_1m_input": 2.0, "cost_per_1m_output": 8.0})

    def _rows(self):
        self.env.flush_all()
        self.env.cr.precommit.run()
        return self.env["integration.exchange"].search(
            [("channel_id", "=", f"integration.service,{self.openai.endpoint_id.id}")],
            order="id desc",
        )

    def _send(self, body):
        client = get_ai_client(self.env, "openai")
        response = self._response(body)
        with patch("requests.Session.request", return_value=response):
            return client.chat_completion([{"role": "user", "content": "q"}])

    @staticmethod
    def _response(body):
        response = Mock(status_code=200, headers={"content-type": "application/json"})
        response.json.return_value = body
        response.text = ""
        response.content = b"{}"
        return response

    def test_a_chat_call_leaves_its_model_tokens_and_cost_on_the_row(self):
        before = len(self._rows())
        self._send(
            {
                "model": "gpt-5.6-luna-2026-08-01",
                "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1_000_000, "completion_tokens": 500_000},
            }
        )

        rows = self._rows()
        self.assertEqual(len(rows) - before, 1)
        row = rows[0]
        self.assertEqual(row.ml_model_id, self.model)
        self.assertEqual(
            (row.ml_input_tokens, row.ml_output_tokens), (1_000_000, 500_000)
        )
        self.assertAlmostEqual(row.ml_cost, 6.0)

    def test_a_response_without_usage_leaves_the_usage_empty(self):
        self._send({"choices": [{"message": {"content": "ok"}}]})

        row = self._rows()[0]
        self.assertFalse(row.ml_model_id)
        self.assertFalse(row.ml_cost)

    def test_a_service_no_provider_rides_records_no_usage(self):
        service = self.env["integration.service"].create(
            {
                "name": "Plain",
                "code": "plain_probe",
                "endpoint_url": "https://example.com",
            }
        )
        self.assertEqual(
            service._exchange_usage_values(
                "https://example.com/x", {}, {"usage": {"prompt_tokens": 5}}
            ),
            {},
        )


@tagged("post_install", "-at_install")
class TestMonthlySpendCap(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.openai = cls.env.ref("gateway_ml.ai_provider_openai")
        connect(cls.env, cls.openai)

    def _spend(self, cost):
        self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": f"integration.service,{self.openai.endpoint_id.id}",
                "company_id": self.company.id,
                "ml_model_id": self.openai._service_for("chat").model_id.id,
                "ml_cost": cost,
            }
        )

    def _call(self):
        client = get_ai_client(self.env, "openai")
        response = Mock(status_code=200, headers={"content-type": "application/json"})
        response.json.return_value = {
            "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}]
        }
        response.text = ""
        response.content = b"{}"
        with patch("requests.Session.request", return_value=response) as sent:
            client.simple_completion("q")
        return sent

    def test_no_cap_sets_no_limit(self):
        self._spend(10_000)
        self.assertTrue(self._call().called)

    def test_spend_under_the_cap_still_calls(self):
        self.company.gateway_ml_monthly_budget = 50
        self._spend(49.5)
        self.assertTrue(self._call().called)
        self.assertAlmostEqual(self.company.gateway_ml_spend_this_month, 49.5)

    def test_a_reached_cap_stops_the_call_before_it_is_sent(self):
        self.company.gateway_ml_monthly_budget = 50
        self._spend(30)
        self._spend(20)
        with (
            patch("requests.Session.request") as sent,
            self.assertRaises(SpendCapReached) as caught,
        ):
            get_ai_client(self.env, "openai").simple_completion("q")
        sent.assert_not_called()
        self.assertIn("50.00", str(caught.exception))

    def test_last_months_spend_does_not_count(self):
        self.company.gateway_ml_monthly_budget = 50
        self._spend(80)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE integration_exchange SET timestamp = timestamp - interval '40 days' "
            "WHERE company_id = %s AND ml_cost = 80",
            (self.company.id,),
        )
        self.env.invalidate_all()
        self.assertTrue(self._call().called)

    def test_a_reached_cap_leaves_the_assistant_quiet_rather_than_raising(self):
        self.company.gateway_ml_monthly_budget = 1
        self._spend(1)
        with patch("requests.Session.request") as sent:
            self.assertIsNone(
                self.openai._assistant().chat_json("sys", "user", 100, 0.1)
            )
        sent.assert_not_called()

    def test_a_service_no_provider_rides_ignores_the_cap(self):
        self.company.gateway_ml_monthly_budget = 1
        self._spend(5)
        service = self.env["integration.service"].create(
            {
                "name": "Plain",
                "code": "plain_cap_probe",
                "endpoint_url": "https://example.com",
            }
        )
        self.assertIsNone(service._check_before_request(self.company.id))
