import pytest

from odoo.orm.runtime._loading_phase import LoadingPhase
from odoo.orm.runtime._registry_loading_phase import _RegistryLoadingPhaseMixin


class _Registry(_RegistryLoadingPhaseMixin):
    __slots__ = ("_loading", "db_name")

    def __init__(self):
        self.db_name = "db"
        self._loading_phase_state()


def test_state_is_created_once_per_key_and_shared():
    phase = LoadingPhase()
    calls = []

    def factory():
        calls.append(1)
        return []

    first = phase.state("addon.key", factory)
    first.append("x")
    assert phase.state("addon.key", factory) is first
    assert phase.state("addon.key", factory) == ["x"]
    assert len(calls) == 1
    assert phase.state("other.key", dict) == {}


def test_loading_is_only_reachable_inside_the_window():
    registry = _Registry()
    assert not registry.is_loading
    with pytest.raises(RuntimeError, match="only available while load_modules"):
        registry.loading
    with registry.loading_window() as phase:
        assert registry.is_loading
        assert registry.loading is phase
        phase.state("addon.key", list[int]).append(1)
        assert registry.loading.state("addon.key", list[int]) == [1]
    with pytest.raises(RuntimeError):
        registry.loading
    assert not registry.is_loading


def test_the_window_does_not_nest():
    registry = _Registry()
    with (
        registry.loading_window(),
        pytest.raises(RuntimeError, match="cannot be nested"),
    ):
        with registry.loading_window():
            pass


def test_recording_xmlids_is_inert_outside_a_load():
    registry = _Registry()
    registry.record_xmlids_written(["a.b"])
    with registry.loading_window() as phase:
        registry.record_xmlids_written(["a.b"])
        assert phase.xmlid_recorder is None
        phase.xmlid_recorder = set()
        registry.record_xmlids_written(["a.b", "a.c"])
        assert phase.xmlid_recorder == {"a.b", "a.c"}
