import contextlib
from types import SimpleNamespace

from odoo.tests.common import warmup


class _Case:
    def __init__(self):
        self.events = []
        self.warm = None
        self.env = SimpleNamespace(
            flush_all=lambda: None,
            invalidate_all=lambda: self.events.append("invalidate"),
        )
        self.cr = SimpleNamespace(savepoint=self._savepoint)

    def _savepoint(self, flush=True):
        case = self

        class _Savepoint:
            def close(self):
                case.events.append("rollback")

        return _Savepoint()

    @warmup
    def measured(self):
        self.events.append(f"run warm={self.warm}")


def test_the_measured_pass_follows_two_rolled_back_cold_passes():
    case = _Case()
    case.measured()
    assert case.events == [
        "invalidate",
        "run warm=False",
        "rollback",
        "invalidate",
        "run warm=False",
        "rollback",
        "invalidate",
        "run warm=True",
    ]


def test_a_failing_cold_pass_still_rolls_back():
    case = _Case()

    @warmup
    def boom(self):
        self.events.append("run")
        raise RuntimeError("boom")

    with contextlib.suppress(RuntimeError):
        boom(case)
    assert case.events == ["invalidate", "run", "rollback"]
