import signal
import unittest
from unittest.mock import patch

import odoo.tools.cache as cache_mod


class TestLogOrmcacheStatsSignalGating(unittest.TestCase):
    def setUp(self):
        cache_mod._logger_state = "wait"
        self.addCleanup(setattr, cache_mod, "_logger_state", "wait")
        self.addCleanup(self._drain)

    def _drain(self):
        for thread in list(__import__("threading").enumerate()):
            if thread.name.startswith("odoo.signal.log_ormcache_stats"):
                thread.join(timeout=10)

    def test_bare_call_starts_and_finishes_a_dump(self):
        with patch.object(
            cache_mod, "_log_ormcache_stats", wraps=cache_mod._log_ormcache_stats
        ) as log_stats:
            cache_mod.log_ormcache_stats()
            self._drain()
            log_stats.assert_called_once_with(False)
        self.assertEqual(
            cache_mod._logger_state,
            "wait",
            "a manual dump must release the state machine after finishing",
        )

    def test_unrelated_signal_does_not_wedge_the_state_machine(self):
        cache_mod.log_ormcache_stats(signal.SIGTERM, None)
        self.assertEqual(cache_mod._logger_state, "wait")

    def test_dump_still_runs_after_a_bare_call(self):
        cache_mod.log_ormcache_stats()
        self._drain()
        cache_mod.log_ormcache_stats(signal.SIGUSR1, None)
        self._drain()
        self.assertEqual(
            cache_mod._logger_state,
            "wait",
            "SIGUSR1 must still start (and finish) a dump",
        )

    def test_repeated_signals_each_run(self):
        for sig in (signal.SIGUSR1, signal.SIGUSR2, signal.SIGUSR1):
            cache_mod.log_ormcache_stats(sig, None)
            self._drain()
            self.assertEqual(cache_mod._logger_state, "wait")


if __name__ == "__main__":
    unittest.main()
