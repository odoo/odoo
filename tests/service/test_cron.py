from unittest.mock import patch

import pytest

from odoo.service import _cron
from odoo.service import settings as server_settings


class TestCronDatabaseList:
    def test_returns_the_configured_databases(self):
        with (
            server_settings.override(db_name=["db1", "db2"]),
            patch("odoo.service._cron.list_dbs") as mock_list,
        ):
            result = _cron.get_cron_databases()
        assert result == ["db1", "db2"]
        mock_list.assert_not_called()

    def test_a_single_configured_database_is_still_a_list(self):
        with (
            server_settings.override(db_name=["mydb"]),
            patch("odoo.service._cron.list_dbs"),
        ):
            result = _cron.get_cron_databases()
        assert list(result) == ["mydb"]

    def test_falls_back_to_list_dbs_when_empty(self):
        with (
            server_settings.override(db_name=[], dbfilter=""),
            patch(
                "odoo.service._cron.list_dbs", return_value=["db1", "db2"]
            ) as mock_list,
        ):
            result = _cron.get_cron_databases()
        mock_list.assert_called_once_with(True)
        assert result == ["db1", "db2"]

    def test_the_result_survives_the_ordered_set_the_callers_build(self):
        from odoo.tools.misc import OrderedSet

        with (
            server_settings.override(db_name=["mydb"]),
            patch("odoo.service._cron.list_dbs"),
        ):
            assert list(OrderedSet(_cron.get_cron_databases())) == ["mydb"]


class TestOrderNotifiedFirst:
    @pytest.fixture
    def order(self):
        from odoo.service._cron import order_notified_first

        return order_notified_first

    def test_notified_come_first_in_notified_order(self, order):
        assert order(["c", "a"], ["a", "b", "c"]) == ["c", "a", "b"]

    def test_stray_notified_for_unknown_db_is_dropped(self, order):
        assert order(["x"], ["a", "b"]) == ["a", "b"]

    def test_empty_notified_preserves_all_dbs_order(self, order):
        assert order([], ["a", "b", "c"]) == ["a", "b", "c"]

    def test_duplicate_notified_yields_db_once(self, order):
        assert order(["a", "a"], ["a", "b"]) == ["a", "b"]
        assert order(["c", "c", "a"], ["a", "b", "c"]) == ["c", "a", "b"]

    def test_duplicate_in_all_dbs_yields_db_once(self, order):
        assert order([], ["a", "a", "b"]) == ["a", "b"]

    @pytest.mark.parametrize("seed", range(20))
    def test_output_is_a_dedup_permutation_of_served_dbs(self, order, seed):
        import random

        rng = random.Random(seed)
        all_dbs = [f"db{i}" for i in range(rng.randint(0, 8))]
        notified = [
            rng.choice(all_dbs)
            if all_dbs and rng.random() < 0.7
            else f"stray{rng.randint(0, 3)}"
            for _ in range(rng.randint(0, 6))
        ]
        result = order(notified, all_dbs)
        assert sorted(result) == sorted(set(all_dbs))
        assert len(result) == len(set(result))
        notified_served = [d for d in dict.fromkeys(notified) if d in set(all_dbs)]
        assert result[: len(notified_served)] == notified_served
