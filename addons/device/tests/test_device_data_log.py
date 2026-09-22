import json
from datetime import timedelta

from lxml import etree

from odoo import Command, fields
from odoo.tests import tagged
from odoo.tools.safe_eval import datetime as safe_datetime
from odoo.tools.safe_eval import safe_eval

from odoo.addons.device.tests.common import DeviceTransactionCase


class TestRemoteDataLog(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Log Test Config",
            },
        )

        cls.device = cls.env["device.device"].create(
            {
                "name": "Log Test Device",
                "identifier": "LOGTEST-001",
                "config_id": cls.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": cls.company.id,
            },
        )

    def test_create_json_data_log(self):
        log = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"temperature": 25.5, "humidity": 60},
                "source_topic": "http://192.168.1.100/api",
                "quality": "good",
            },
        )

        self.assertEqual(log.device_id, self.device)
        self.assertEqual(log.data_type, "json")
        self.assertEqual(log.value_json["temperature"], 25.5)
        self.assertEqual(log.quality, "good")
        self.assertIsNotNone(log.timestamp)

    def test_create_text_data_log(self):
        log = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "text",
                "value_text": "Device status: OK",
            },
        )

        self.assertEqual(log.data_type, "text")
        self.assertEqual(log.value_text, "Device status: OK")

    def test_data_type_selection(self):
        data_types = ["json", "text", "numeric", "boolean"]

        for data_type in data_types:
            log = self.env["device.data.log"].create(
                {
                    "device_id": self.device.id,
                    "data_type": data_type,
                    "value_text": "test",
                },
            )
            self.assertEqual(log.data_type, data_type)

    def test_quality_selection(self):
        qualities = ["good", "bad", "uncertain"]

        for quality in qualities:
            log = self.env["device.data.log"].create(
                {
                    "device_id": self.device.id,
                    "data_type": "json",
                    "value_json": {"test": True},
                    "quality": quality,
                },
            )
            self.assertEqual(log.quality, quality)

    def test_timestamp_auto_set(self):
        before = fields.Datetime.now()

        log = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"test": True},
            },
        )

        after = fields.Datetime.now()

        self.assertIsNotNone(log.timestamp)
        self.assertGreaterEqual(log.timestamp, before)
        self.assertLessEqual(log.timestamp, after)

    def test_raw_payload_storage(self):
        raw = '{"temperature": 25.5, "unit": "celsius"}'

        log = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": json.loads(raw),
                "raw_payload": raw,
            },
        )

        self.assertEqual(log.raw_payload, raw)

    def test_source_topic_storage(self):
        topic = "devices/sensor-001/telemetry"

        log = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"temp": 20},
                "source_topic": topic,
            },
        )

        self.assertEqual(log.source_topic, topic)


class TestRemoteDataLogRetention(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Retention Test Config",
            },
        )

        cls.device = cls.env["device.device"].create(
            {
                "name": "Retention Test Device",
                "identifier": "RETENTION-001",
                "config_id": cls.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.100",
                "company_id": cls.company.id,
            },
        )

    def test_create_multiple_logs(self):
        logs = self.env["device.data.log"]

        for i in range(10):
            log = self.env["device.data.log"].create(
                {
                    "device_id": self.device.id,
                    "data_type": "json",
                    "value_json": {"reading": i, "temp": 20 + i},
                },
            )
            logs |= log

        self.assertEqual(len(logs), 10)

    def test_filter_logs_by_device(self):
        device2 = self.env["device.device"].create(
            {
                "name": "Device 2",
                "identifier": "DEVICE-002",
                "config_id": self.config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.1.101",
                "company_id": self.company.id,
            },
        )

        for i in range(5):
            self.env["device.data.log"].create(
                {
                    "device_id": self.device.id,
                    "data_type": "json",
                    "value_json": {"device": 1, "val": i},
                },
            )
            self.env["device.data.log"].create(
                {
                    "device_id": device2.id,
                    "data_type": "json",
                    "value_json": {"device": 2, "val": i},
                },
            )

        device1_logs = self.env["device.data.log"].search(
            [("device_id", "=", self.device.id)],
        )
        device2_logs = self.env["device.data.log"].search(
            [("device_id", "=", device2.id)],
        )

        self.assertEqual(len(device1_logs), 5)
        self.assertEqual(len(device2_logs), 5)

    def test_filter_logs_by_quality(self):
        self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"good": True},
                "quality": "good",
            },
        )
        self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"bad": True},
                "quality": "bad",
            },
        )

        good_logs = self.env["device.data.log"].search(
            [("device_id", "=", self.device.id), ("quality", "=", "good")],
        )
        bad_logs = self.env["device.data.log"].search(
            [("device_id", "=", self.device.id), ("quality", "=", "bad")],
        )

        self.assertEqual(len(good_logs), 1)
        self.assertEqual(len(bad_logs), 1)


class TestRemoteDataLogSearch(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")

        cls.config = cls.env["device.profile"].create(
            {
                "name": "Search Test Config",
            },
        )

        cls.device = cls.env["device.device"].create(
            {
                "name": "Search Test Device",
                "identifier": "SEARCH-001",
                "config_id": cls.config.id,
                "comm_protocol": "http",
                "endpoint": "sensor.example.com",
                "company_id": cls.company.id,
            },
        )

    def test_search_by_source_topic(self):
        self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"temp": 20},
                "source_topic": "devices/sensor/temperature",
            },
        )
        self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"humidity": 60},
                "source_topic": "devices/sensor/humidity",
            },
        )

        temp_logs = self.env["device.data.log"].search(
            [("source_topic", "ilike", "temperature")],
        )

        self.assertEqual(len(temp_logs), 1)
        self.assertIn("temperature", temp_logs.source_topic)

    def test_search_by_data_type(self):
        self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"test": True},
            },
        )
        self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "text",
                "value_text": "plain text message",
            },
        )

        json_logs = self.env["device.data.log"].search(
            [("device_id", "=", self.device.id), ("data_type", "=", "json")],
        )

        self.assertEqual(len(json_logs), 1)


@tagged("post_install", "-at_install")
class TestRemoteDataLogReportCompanyScope(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.ref("base.main_company")
        cls.company_b = cls.env["res.company"].create({"name": "Remote Co B"})
        config = cls.env["device.profile"].create({"name": "Scope Config"})
        cls.device_a = cls.env["device.device"].create(
            {
                "name": "Device A",
                "identifier": "SCOPE-REMOTE-A",
                "config_id": config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.3.10",
                "company_id": cls.company_a.id,
            }
        )
        cls.device_b = cls.env["device.device"].create(
            {
                "name": "Device B",
                "identifier": "SCOPE-REMOTE-B",
                "config_id": config.id,
                "comm_protocol": "http",
                "endpoint": "192.168.3.20",
                "company_id": cls.company_b.id,
            }
        )
        for device in (cls.device_a, cls.device_b):
            cls.env["device.data.log"].create(
                {
                    "device_id": device.id,
                    "data_type": "json",
                    "value_json": {"k": "v"},
                }
            )
        cls.env.flush_all()
        cls.report = cls.env["device.data.log.report"]
        cls.report.refresh()

        cls.user_a = cls.env["res.users"].create(
            {
                "name": "Remote User A",
                "login": "remote_scope_user_a",
                "group_ids": [Command.link(cls.env.ref("device.group_device_user").id)],
                "company_ids": [Command.set([cls.company_a.id])],
                "company_id": cls.company_a.id,
            }
        )

    def test_report_scoped_to_reader_company(self):
        visible = self.report.with_user(self.user_a).search([])
        companies = visible.mapped("company_id")

        self.assertIn(self.company_a, companies, "own-company rows are visible")
        self.assertNotIn(
            self.company_b, companies, "another company's telemetry must not leak"
        )


class TestRawPayloadRetention(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.device = cls._create_device_device(identifier="RAW-RETAIN")

    def _log_at(self, days_ago, payload='{"raw": 1}'):
        return self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "timestamp": fields.Datetime.now() - timedelta(days=days_ago),
                "raw_payload": payload,
            }
        )

    def _set_retention(self, days):
        self.env["ir.config_parameter"].sudo().set_param(
            "device.raw_payload_retention_days", str(days)
        )

    def test_nothing_is_discarded_by_default(self):
        self._set_retention(0)
        old = self._log_at(400)

        self.env["device.data.log"]._gc_old_raw_payloads()

        self.assertTrue(
            old.raw_payload,
            "raw payloads must not start disappearing because a module was "
            "upgraded; discarding them cannot be undone",
        )

    def test_payloads_past_the_window_are_discarded(self):
        self._set_retention(30)
        old = self._log_at(90)
        recent = self._log_at(5)

        cleared = self.env["device.data.log"]._gc_old_raw_payloads()

        self.assertEqual(cleared, 1)
        self.assertFalse(old.raw_payload)
        self.assertTrue(recent.raw_payload)

    def test_the_row_and_its_parsed_columns_survive(self):
        self._set_retention(30)
        old = self._log_at(90)
        old.write({"value_text": "parsed"})

        self.env["device.data.log"]._gc_old_raw_payloads()

        self.assertTrue(old.exists())
        self.assertEqual(old.value_text, "parsed")

    def test_a_second_pass_finds_nothing_left_to_do(self):
        self._set_retention(30)
        self._log_at(90)

        self.assertEqual(self.env["device.data.log"]._gc_old_raw_payloads(), 1)
        self.assertEqual(self.env["device.data.log"]._gc_old_raw_payloads(), 0)


@tagged("post_install", "-at_install")
class TestLogMixinApiIsGeneric(DeviceTransactionCase):
    """The mixin's public surface must run on every model that inherits it."""

    def _models_inheriting_the_log_mixin(self):
        return sorted(
            name
            for name, model in self.env.registry.items()
            if not model._abstract and "mixin.device.data.log" in model._inherit
        )

    def test_the_mixin_is_inherited_by_more_than_one_model(self):
        models = self._models_inheriting_the_log_mixin()
        if len(models) < 2:
            # `remote` installed on its own is the supported configuration and
            # what CI runs for this module's own tag. The mixin's genericity is
            # only observable once a sibling contributes a second concrete
            # model, so this check waits for one instead of failing without it.
            self.skipTest(
                f"only {models} inherits the mixin; install a sibling such as "
                "device_gps to exercise its genericity",
            )
        self.assertGreater(len(models), 1)

    def test_every_mixin_method_runs_on_every_model_that_inherits_it(self):
        device = self.env["device.device"].search([], limit=1)
        for name in self._models_inheriting_the_log_mixin():
            model = self.env[name]
            with self.subTest(model=name):
                model.get_log_last_ids(device)
                model._gc_old_raw_payloads()


@tagged("post_install", "-at_install")
class TestLogIndexes(DeviceTransactionCase):
    """The composite is what serves device lookups; a second btree is not."""

    def _indexes(self, table):
        self.env.cr.execute(
            "SELECT indexname FROM pg_indexes WHERE tablename = %s", (table,)
        )
        return {row[0] for row in self.env.cr.fetchall()}

    def _log_tables(self):
        return [
            self.env[name]._table
            for name, model in self.env.registry.items()
            if not model._abstract and "mixin.device.data.log" in model._inherit
        ]

    def test_every_log_table_keeps_the_composite_that_leads_with_the_device(self):
        for table in self._log_tables():
            with self.subTest(table=table):
                self.assertIn(f"{table}_device_timestamp_idx", self._indexes(table))

    def test_no_log_table_carries_a_second_btree_on_the_device_alone(self):
        offenders = {
            table
            for table in self._log_tables()
            if f"{table}__device_id_index" in self._indexes(table)
        }
        self.assertFalse(
            offenders,
            "the composite index leads with device_id, so a btree on device_id "
            f"alone answers nothing it does not and costs every insert: {offenders}",
        )


class TestDataLogSearchFilters(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Filter Test Config")
        cls.device = cls._create_device_device(
            config=cls.config, identifier="FILTER-001"
        )

    def _filter_domain(self, name):
        view = self.env.ref("device.view_device_data_log_search")
        arch = etree.fromstring(view.arch)
        node = arch.xpath(f"//filter[@name='{name}']")[0]
        return safe_eval(
            node.get("domain"),
            {
                "context_today": lambda: fields.Date.context_today(self.device),
                "datetime": safe_datetime,
            },
        )

    def _log(self, timestamp):
        log = self.env["device.data.log"].create(
            {
                "device_id": self.device.id,
                "data_type": "json",
                "value_json": {"probe": 1},
            },
        )
        log.timestamp = timestamp
        return log

    def test_every_date_filter_of_the_search_view_evaluates_to_a_domain(self):
        for name in ("filter_today", "filter_last_week"):
            with self.subTest(filter=name):
                domain = self._filter_domain(name)
                self.assertNotIn(
                    "function",
                    repr(domain),
                    f"{name} leaves a callable in the domain instead of a date",
                )
                self.env["device.data.log"].search(domain)

    def test_the_default_filter_of_the_data_log_action_returns_todays_rows(self):
        today = self._log(fields.Datetime.now())
        yesterday = self._log(fields.Datetime.now() - timedelta(days=1))

        action = self.env.ref("device.action_device_data_log")
        self.assertEqual(
            safe_eval(action.context).get("search_default_filter_today"),
            1,
            "the action still opens on the Today filter",
        )

        found = self.env["device.data.log"].search(
            [*self._filter_domain("filter_today"), ("device_id", "=", self.device.id)]
        )
        self.assertIn(today, found)
        self.assertNotIn(yesterday, found)
