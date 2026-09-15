import hashlib
import json
from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.libs.logging import mute_logger
from odoo.tests.common import TransactionCase


class TestIntegrationExchange(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.service = (
            cls.env["integration.service"]
            .with_context(allow_http_production=True)
            .create(
                {
                    "name": "Test Service",
                    "code": "test_service",
                    "endpoint_url": "https://api.test.com",
                    "company_id": cls.company.id,
                },
            )
        )

        cls.channel_ref = f"integration.service,{cls.service.id}"

    def _create_event_log(self, **kwargs):
        default_vals = {
            "direction": "outbound",
            "channel_id": self.channel_ref,
            "state": "pending",
        }
        default_vals.update(kwargs)
        return self.env["integration.exchange"].create(default_vals)

    def test_create_outbound_event(self):
        event = self._create_event_log(
            request_method="POST",
            request_url="https://api.test.com/v1/endpoint",
            request_payload='{"key": "value"}',
        )

        self.assertEqual(event.direction, "outbound")
        self.assertEqual(event.request_method, "POST")
        self.assertEqual(event.state, "pending")
        self.assertIsNotNone(event.timestamp)

    def test_create_inbound_event(self):
        event = self._create_event_log(
            direction="inbound",
            request_payload='{"event": "test"}',
            source_ip="192.168.1.100",
        )

        self.assertEqual(event.direction, "inbound")
        self.assertEqual(event.source_ip, "192.168.1.100")

    def test_payload_hash_computation(self):
        payload = '{"key": "value", "number": 123}'
        event = self._create_event_log(request_payload=payload)

        parsed = json.loads(payload)
        normalized = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        expected_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

        self.assertEqual(event.request_payload_hash, expected_hash)

    def test_payload_hash_normalization(self):
        payload1 = '{"b": 2, "a": 1}'
        payload2 = '{"a": 1, "b": 2}'

        event1 = self._create_event_log(request_payload=payload1)
        event2 = self._create_event_log(request_payload=payload2)

        self.assertEqual(event1.request_payload_hash, event2.request_payload_hash)

    def test_payload_sizes_computation(self):
        request_payload = '{"key": "value"}'
        response_payload = '{"status": "ok"}'

        event = self._create_event_log(
            request_payload=request_payload,
            response_payload=response_payload,
        )

        self.assertEqual(
            event.request_payload_size, len(request_payload.encode("utf-8"))
        )
        self.assertEqual(
            event.response_payload_size, len(response_payload.encode("utf-8"))
        )

    def test_status_category_computation(self):
        test_cases = [
            (200, "success"),
            (201, "success"),
            (204, "success"),
            (301, "redirect"),
            (302, "redirect"),
            (400, "client_error"),
            (401, "client_error"),
            (404, "client_error"),
            (500, "server_error"),
            (503, "server_error"),
            (None, "unknown"),
        ]

        for status_code, expected_category in test_cases:
            event = self._create_event_log(status_code=status_code)
            self.assertEqual(
                event.status_category,
                expected_category,
                f"Status {status_code} should be '{expected_category}', got '{event.status_category}'",
            )

    def test_is_success_computation_outbound(self):
        success_event = self._create_event_log(status_code=200)
        self.assertTrue(success_event.is_success)

        redirect_event = self._create_event_log(status_code=302)
        self.assertTrue(redirect_event.is_success)

        failed_event = self._create_event_log(status_code=500)
        self.assertFalse(failed_event.is_success)

    def test_is_success_computation_inbound(self):
        success_event = self._create_event_log(direction="inbound", state="success")
        self.assertTrue(success_event.is_success)

        failed_event = self._create_event_log(direction="inbound", state="failed")
        self.assertFalse(failed_event.is_success)

    def test_performance_rating_computation(self):
        test_cases = [
            (50, "excellent"),
            (100, "good"),
            (450, "good"),
            (500, "average"),
            (999, "average"),
            (1000, "slow"),
            (2999, "slow"),
            (3000, "very_slow"),
            (10000, "very_slow"),
        ]

        for duration, expected_rating in test_cases:
            event = self._create_event_log(duration_ms=duration)
            self.assertEqual(
                event.performance_rating,
                expected_rating,
                f"Duration {duration}ms should be '{expected_rating}', got '{event.performance_rating}'",
            )

    def test_mark_processing(self):
        event = self._create_event_log()
        event.mark_processing()

        self.assertEqual(event.state, "processing")

    def test_mark_success(self):
        event = self._create_event_log()
        event.mark_success()

        self.assertEqual(event.state, "success")
        self.assertIsNotNone(event.date_completed)
        self.assertFalse(event.error_message)

    def test_mark_failed(self):
        event = self._create_event_log()
        event.mark_failed("Network timeout", error_type="timeout", schedule_retry=False)

        self.assertEqual(event.state, "failed")
        self.assertEqual(event.error_message, "Network timeout")
        self.assertEqual(event.error_type, "timeout")
        self.assertEqual(event.retry_count, 1)

    def test_mark_duplicate(self):
        event = self._create_event_log()
        event.mark_duplicate()

        self.assertEqual(event.state, "duplicate")
        self.assertEqual(event.error_type, "duplicate")
        self.assertIsNotNone(event.date_completed)

    def test_action_retry_now(self):
        event = self._create_event_log(state="failed")

        result = event.action_retry_now()

        self.assertEqual(event.state, "pending")
        self.assertIsNotNone(event.date_next_retry)
        self.assertEqual(result["type"], "ir.actions.client")

    def test_action_retry_now_invalid_state(self):
        event = self._create_event_log(state="success")

        with self.assertRaises(ValidationError):
            event.action_retry_now()

    def test_action_view_channel(self):
        event = self._create_event_log()

        result = event.action_view_channel()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertEqual(result["res_model"], "integration.service")
        self.assertEqual(result["res_id"], self.service.id)

    def test_action_view_related_events(self):
        trace_id = "trace-12345"
        event = self._create_event_log(trace_id=trace_id)

        result = event.action_view_related_events()

        self.assertEqual(result["type"], "ir.actions.act_window")
        self.assertIn(trace_id, str(result["domain"]))

    def test_action_view_related_events_no_trace(self):
        event = self._create_event_log()

        result = event.action_view_related_events()

        self.assertIsNone(result)

    def test_get_payload_dict(self):
        payload = '{"key": "value", "number": 123}'
        event = self._create_event_log(request_payload=payload)

        result = event.get_payload_dict()

        self.assertEqual(result["key"], "value")
        self.assertEqual(result["number"], 123)

    @mute_logger("odoo.addons.integration.models.integration_exchange")
    def test_get_payload_dict_invalid_json(self):
        event = self._create_event_log(request_payload="not valid json")

        result = event.get_payload_dict()

        self.assertEqual(result, {})

    def test_check_duplicate_before_create_by_external_id(self):
        external_id = "ext-event-123"
        self._create_event_log(event_id_external=external_id)

        result = self.env["integration.exchange"].get_duplicate_info(
            channel_ref=self.channel_ref,
            payload_json='{"any": "data"}',
            event_id_external=external_id,
        )

        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["reason"], "external_id")

    def test_check_duplicate_before_create_by_hash(self):
        payload = '{"key": "value"}'
        self._create_event_log(request_payload=payload)

        result = self.env["integration.exchange"].get_duplicate_info(
            channel_ref=self.channel_ref,
            payload_json=payload,
            dedup_window_hours=1,
        )

        self.assertTrue(result["is_duplicate"])
        self.assertEqual(result["reason"], "payload_hash")

    def test_check_duplicate_before_create_no_duplicate(self):
        result = self.env["integration.exchange"].get_duplicate_info(
            channel_ref=self.channel_ref,
            payload_json='{"unique": "payload"}',
        )

        self.assertFalse(result["is_duplicate"])
        self.assertIsNone(result["reason"])

    def test_display_name_computation(self):
        event = self._create_event_log(
            request_method="POST",
        )

        self.assertIn("OU", event.display_name)
        self.assertIn("POST", event.display_name)

    def test_request_endpoint_extraction(self):
        event = self._create_event_log(
            request_url="https://api.test.com/v1/endpoint/action",
        )

        self.assertIn("/", event.request_endpoint)


class TestIntegrationExchangeRetention(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.service = (
            cls.env["integration.service"]
            .with_context(allow_http_production=True)
            .create(
                {
                    "name": "Test Service",
                    "code": "test_gc",
                    "endpoint_url": "https://api.test.com",
                    "company_id": cls.company.id,
                },
            )
        )
        cls.channel_ref = f"integration.service,{cls.service.id}"

    def test_gc_respects_retention_setting(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "integration.log_retention_days",
            "30",
        )

        old_event = self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": self.channel_ref,
                "state": "success",
                "date_completed": fields.Datetime.now() - timedelta(days=60),
            },
        )

        recent_event = self.env["integration.exchange"].create(
            {
                "direction": "outbound",
                "channel_id": self.channel_ref,
                "state": "success",
                "date_completed": fields.Datetime.now() - timedelta(days=10),
            },
        )

        self.env["integration.exchange"]._gc_old_logs()

        self.assertFalse(old_event.exists())
        self.assertTrue(recent_event.exists())


class TestInboundEventEnqueue(TestIntegrationExchange):
    """One event, one job, however many callers ask for it."""

    def _jobs_for(self, event):
        return self.env["ir.job"].search(
            [("identity_key", "=", f"integration.event:{event.id}")]
        )

    def _give_the_channel_a_handler(self, handler):
        # Not `self.patch`, which requires the attribute to exist:
        # `_run_queued_event` lives on the INBOUND mixin, and the channel these
        # events point at is an outbound endpoint because `mixin.integration.receiver`
        # is abstract and has no concrete model in this addon to point at.
        channel_cls = self.registry["integration.service"]
        channel_cls._run_queued_event = handler
        self.addCleanup(delattr, channel_cls, "_run_queued_event")

    def _inbound_event(self):
        event = self._create_event_log(direction="inbound")
        self.env["ir.job"].search([]).unlink()
        return event

    def _give_the_channel_a_processing_mode(self, processing_mode):
        # `processing_mode` lives on the INBOUND mixin too; see
        # `_give_the_channel_a_handler` above for why it is patched onto the
        # outbound channel these test events point at.
        channel_cls = self.registry["integration.service"]
        channel_cls.processing_mode = processing_mode
        self.addCleanup(delattr, channel_cls, "processing_mode")

    def test_enqueuing_the_same_event_twice_leaves_one_job(self):
        event = self._inbound_event()

        event._enqueue_processing()
        event._enqueue_processing()

        self.assertEqual(len(self._jobs_for(event)), 1)

    def test_the_retry_cron_does_not_add_a_second_job_for_a_fresh_event(self):
        # The defect this guards: `queue_event` leaves an event `pending` with
        # `date_next_retry` unset, and the cron's domain asks for exactly that.
        # Any cron run between queueing and the worker claiming the job used to
        # enqueue a second one, and nothing downstream deduplicated it.
        self._give_the_channel_a_handler(lambda channel, event_id: None)
        event = self._inbound_event()
        event._enqueue_processing()

        self.env["integration.exchange"]._cron_retry_failed_events()

        self.assertEqual(
            len(self._jobs_for(event)),
            1,
            "the cron must not hand a worker an event another worker already has",
        )

    @mute_logger("odoo.addons.integration.models.integration_exchange")
    def test_the_retry_cron_does_not_replay_a_synchronous_endpoints_event(self):
        # The defect this guards: `queue_event` never enqueues a job for a
        # `processing_mode="sync"` endpoint (the caller is expected to process
        # inline and close the event itself), so a caller that forgets leaves
        # the event `pending` with no job to deduplicate against. The cron
        # used to enqueue one anyway right after warning that it shouldn't.
        self._give_the_channel_a_handler(lambda channel, event_id: None)
        self._give_the_channel_a_processing_mode("sync")
        event = self._inbound_event()

        self.env["integration.exchange"]._cron_retry_failed_events()

        self.assertEqual(
            len(self._jobs_for(event)),
            0,
            "a synchronous endpoint's event must not be handed to a worker",
        )
        self.assertEqual(event.state, "pending")

    def test_the_job_hands_the_event_to_its_channel(self):
        seen = []
        self._give_the_channel_a_handler(
            lambda channel, event_id: seen.append(event_id)
        )
        event = self._inbound_event()

        event._job_process_inbound()

        self.assertEqual(seen, [event.id])

    def test_an_event_whose_channel_cannot_process_it_fails_rather_than_raising(self):
        event = self._inbound_event()

        event._job_process_inbound()

        self.assertEqual(event.state, "failed")
