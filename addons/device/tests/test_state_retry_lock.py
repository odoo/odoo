import time
from unittest.mock import patch

from odoo.tests import tagged

from .common import DeviceTransactionCase


@tagged("post_install", "-at_install")
class TestStateRetryLockTimeout(DeviceTransactionCase):
    def _run_against_a_locked_table(self, timeout):
        Device = self.env["device.device"]
        calls = []

        def _touch(fresh_env):
            calls.append(fresh_env["device.device"].search_count([]))
            return "ran"

        self.env.cr.execute("LOCK TABLE device_device IN ACCESS EXCLUSIVE MODE")
        with patch.object(type(Device), "_STATE_LOCK_TIMEOUT", timeout):
            started = time.monotonic()
            result = Device._run_with_state_retry(_touch, "lock timeout probe")
            elapsed = time.monotonic() - started
        return result, elapsed, calls

    def test_a_locked_table_is_skipped_rather_than_waited_on(self):
        result, elapsed, calls = self._run_against_a_locked_table("300ms")

        self.assertIsNone(
            result,
            "a lock it could not take must be reported as a dropped write",
        )
        self.assertEqual(calls, [], "the body must not have run")
        self.assertLess(
            elapsed,
            30,
            "the reset waited on the lock instead of giving up; on a real "
            "upgrade the loader holds it and this never returns",
        )

    def test_the_timeout_is_what_bounds_the_wait(self):
        _result, quick, _calls = self._run_against_a_locked_table("100ms")
        self.assertLess(quick, 5, "a 100ms cap must return in well under 5s")
