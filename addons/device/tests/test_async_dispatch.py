import json

from odoo.tests.common import tagged

from odoo.addons.device.tests.common import DeviceHttpCase, DeviceTransactionCase


class TestAsyncDispatch(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["device.profile"].create({"name": "Async Dispatch Config"})
        cls.device = cls.env["device.device"].create(
            {
                "name": "Async Device",
                "identifier": "ASYNC-1",
                "config_id": cls.config.id,
                "comm_protocol": "http",
                "endpoint": "10.0.0.9",
                "processing_mode": "async",
            }
        )

    def test_queue_event_enqueues_a_job_for_the_event(self):
        event = self.device.queue_event({"temperature": 21.5})

        # integration routes an async event through its own event log, whose
        # identity_key is what stops the same payload being handled twice.
        job = self.env["ir.job"].search(
            [
                ("model_name", "=", "integration.exchange"),
                ("method_name", "=", "_job_process_inbound"),
            ],
            order="id desc",
            limit=1,
        )
        self.assertTrue(job, "queue_event must enqueue a job")
        self.assertEqual(list(job.record_ids), [event.id])
        self.assertEqual(job.identity_key, f"integration.event:{event.id}")
        self.assertEqual(
            job.max_retries,
            0,
            "retry policy belongs to _cron_retry_failed_events, which leases "
            "events to avoid double-dispatch",
        )

    def test_a_second_enqueue_of_the_same_event_does_not_double_dispatch(self):
        event = self.device.queue_event({"temperature": 21.5})

        event._enqueue_processing()

        jobs = self.env["ir.job"].search(
            [("identity_key", "=", f"integration.event:{event.id}")]
        )
        self.assertEqual(
            len(jobs), 1, "the identity key must collapse a repeated enqueue"
        )

    def test_queue_event_reuses_a_supplied_event_log(self):
        existing = self.env["integration.exchange"].create(
            {
                "direction": "inbound",
                "channel_id": f"device.device,{self.device.id}",
                "request_payload": "{}",
                "state": "pending",
            }
        )
        before = self.env["integration.exchange"].search_count([])

        event = self.device.queue_event({"a": 1}, event_log=existing)

        self.assertEqual(event, existing)
        self.assertEqual(self.env["integration.exchange"].search_count([]), before)

    def test_run_queued_event_dispatches_to_process_queued_event(self):
        event = self.env["integration.exchange"].create(
            {
                "direction": "inbound",
                "channel_id": f"device.device,{self.device.id}",
                "request_payload": '{"temperature": 21.5}',
                "state": "pending",
            }
        )

        self.device._run_queued_event(event.id)

        self.assertEqual(event.state, "success")

    def test_run_queued_event_survives_a_deleted_event(self):
        event = self.env["integration.exchange"].create(
            {
                "direction": "inbound",
                "channel_id": f"device.device,{self.device.id}",
                "request_payload": "{}",
                "state": "pending",
            }
        )
        event_id = event.id
        event.unlink()

        self.device._run_queued_event(event_id)

    def test_device_handler_stores_the_payload(self):
        event = self.env["integration.exchange"].create(
            {
                "direction": "inbound",
                "channel_id": f"device.device,{self.device.id}",
                "request_payload": '{"temperature": 21.5}',
                "state": "pending",
            }
        )

        self.device._process_queued_event(event)

        self.assertEqual(event.state, "success")
        log = self.env["device.data.log"].search(
            [("device_id", "=", self.device.id)], limit=1
        )
        self.assertEqual(log.value_json, {"temperature": 21.5})
        self.assertEqual(log.source, "webhook")
        self.assertEqual(log.source_topic, f"http_push/{self.device.identifier}")


@tagged("post_install", "-at_install")
class TestPushRouteStoresOneSource(DeviceHttpCase):
    # The push route reached _store_data_point twice with different arguments:
    # the sync branch named source="webhook", the async branch let the signature
    # default to "iot". device.data.log.report groups and filters by source, so
    # the same device landed in two analytics buckets depending on a field no
    # view exposes.

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Push Route Config")
        cls.device = cls._create_device_device(
            config=cls.config,
            name="Push Route Device",
            identifier="PUSH-ROUTE",
            endpoint="10.0.0.9",
        )
        cls.token = cls._device_token(cls.device)

    def _push(self):
        self.env.flush_all()
        return self.url_open(
            f"/remote/device/{self.device.identifier}/data",
            data=json.dumps({"temperature": 21.5}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

    def _last_event(self):
        return self.env["integration.exchange"].search(
            [("channel_id", "=", f"device.device,{self.device.id}")],
            order="id desc",
            limit=1,
        )

    def test_both_processing_modes_store_the_same_source(self):
        self.device.processing_mode = "sync"
        self.assertEqual(self._push().status_code, 200)

        self.device.processing_mode = "async"
        self.assertEqual(self._push().status_code, 202)
        self.device._run_queued_event(self._last_event().id)

        rows = self.env["device.data.log"].search(
            [("device_id", "=", self.device.id)], order="id"
        )
        self.assertEqual(len(rows), 2, "one row per push")
        self.assertEqual(rows.mapped("source"), ["webhook", "webhook"])
        self.assertEqual(
            rows.mapped("source_topic"),
            [f"http_push/{self.device.identifier}"] * 2,
        )


@tagged("post_install", "-at_install")
class TestStatusPollLeavesNoOpenExchange(DeviceHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.device = cls._create_device_device(
            config=cls._create_device_profile(name="Status Poll Config"),
            name="Status Poll Device",
            identifier="STATUS-POLL",
        )
        cls.token = cls._device_token(cls.device)

    def _exchanges(self):
        return self.env["integration.exchange"].search_count(
            [("channel_id", "=", f"device.device,{self.device.id}")]
        )

    def test_a_status_read_answers_without_opening_an_exchange(self):
        self.env.flush_all()
        before = self._exchanges()

        response = self.url_open(
            f"/remote/device/{self.device.identifier}/status",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["device"]["identifier"], "STATUS-POLL")
        self.assertEqual(self._exchanges(), before)
