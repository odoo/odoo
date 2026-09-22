from datetime import timedelta

from odoo import fields

from odoo.addons.device.tests.common import DeviceTransactionCase


class TestLastLogPointer(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Pointer Config")
        cls.device = cls._create_device_device(
            config=cls.config, identifier="POINTER-1"
        )

    def test_storing_a_point_moves_the_pointer(self):
        self.assertFalse(self.device.log_last_id)

        first = self.device._store_data_point({"t": 1}, source_topic="test")
        self.device.invalidate_recordset()
        self.assertEqual(self.device.log_last_id, first)

        second = self.device._store_data_point({"t": 2}, source_topic="test")
        self.device.invalidate_recordset()
        self.assertEqual(self.device.log_last_id, second)

    def test_the_pointer_is_per_device(self):
        other = self._create_device_device(config=self.config, identifier="POINTER-2")
        mine = self.device._store_data_point({"t": 1}, source_topic="test")
        theirs = other._store_data_point({"t": 2}, source_topic="test")
        self.device.invalidate_recordset()
        other.invalidate_recordset()
        self.assertEqual(self.device.log_last_id, mine)
        self.assertEqual(other.log_last_id, theirs)

    def test_reading_the_pointer_costs_no_aggregate(self):
        for index in range(30):
            self.device._store_data_point({"t": index}, source_topic="test")
        self.env.flush_all()
        self.env.invalidate_all()

        before = self.env.cr.sql_statement_count
        self.assertTrue(self.device.log_last_id)
        queries = self.env.cr.sql_statement_count - before
        self.assertLessEqual(
            queries,
            2,
            f"reading log_last_id issued {queries} queries — it is being "
            f"aggregated again rather than read from the device row",
        )


class TestWindowedLogCounts(DeviceTransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Counting Config")
        cls.device = cls._create_device_device(
            config=cls.config, identifier="COUNTING-1"
        )

    def _log_at(self, model, days_ago, **extra):
        vals = {
            "device_id": self.device.id,
            "timestamp": fields.Datetime.now() - timedelta(days=days_ago),
            "data_type": "json",
        }
        vals.update(extra)
        return self.env[model].create(vals)

    def test_log_count_ignores_history_outside_the_window(self):
        for days in (0, 0, 30, 90, 400):
            self._log_at("device.data.log", days, value_json={"t": 1})
        self.device.invalidate_recordset()
        self.assertEqual(
            self.device.log_count,
            2,
            "log_count is counting the device's whole history again",
        )

    def test_a_silent_device_counts_zero(self):
        self._log_at("device.data.log", 30, value_json={"t": 1})
        self.device.invalidate_recordset()
        self.assertEqual(self.device.log_count, 0)

    def test_the_window_is_shared_by_both_counts(self):
        self.assertEqual(
            type(self.device)._LOG_COUNT_WINDOW_HOURS,
            24,
            "the documented window and the field labels must agree",
        )


class TestRelationCounts(DeviceTransactionCase):
    # device.profile.device_count and device.kind.device_count were
    # hand-rolled _read_group computes. They had already drifted: the profile
    # declared @api.depends("device_ids"), the category declared nothing, and
    # neither of them noticed a device being archived.

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls._create_device_profile(name="Relation Count Config")
        cls.category = cls.env["device.kind"].create(
            {"name": "Relation Count Category", "code": "REL-COUNT"},
        )

    def test_both_counts_follow_a_create_in_the_same_transaction(self):
        self.assertEqual(self.config.device_count, 0)
        self.assertEqual(self.category.device_count, 0)

        self._create_device_device(
            config=self.config,
            identifier="REL-COUNT-1",
            device_category_id=self.category.id,
        )

        self.assertEqual(self.config.device_count, 1)
        self.assertEqual(self.category.device_count, 1)

    def test_both_counts_follow_an_archive_and_back(self):
        device = self._create_device_device(
            config=self.config,
            identifier="REL-COUNT-2",
            device_category_id=self.category.id,
        )
        self.assertEqual(self.config.device_count, 1)
        self.assertEqual(self.category.device_count, 1)

        device.active = False

        self.assertEqual(self.config.device_count, 0)
        self.assertEqual(self.category.device_count, 0)

        device.active = True

        self.assertEqual(self.config.device_count, 1)
        self.assertEqual(self.category.device_count, 1)

    def test_the_counts_stay_out_of_the_database(self):
        for model in ("device.profile", "device.kind"):
            field = self.env[model]._fields["device_count"]
            self.assertFalse(
                field.store,
                f"{model}.device_count must stay unstored: it had no column "
                f"before and adding one needs a migration",
            )
            self.assertTrue(
                field.counts_in_database,
                f"{model}.device_count must still aggregate in one query "
                f"rather than reading every related row",
            )
