from odoo.libs.settings import SettingsSlot


class _Source:
    def __init__(self) -> None:
        self.reads = 0

    def __call__(self) -> object:
        self.reads += 1
        return object()


def test_without_a_version_every_read_derives():
    source = _Source()
    slot = SettingsSlot("t", source)
    assert slot.current() is not slot.current()
    assert source.reads == 2


def test_with_a_version_the_snapshot_is_reused_until_the_version_moves():
    version = [0]
    source = _Source()
    slot = SettingsSlot("t", source, version=lambda: version[0])
    first = slot.current()
    assert slot.current() is first
    assert source.reads == 1
    version[0] += 1
    second = slot.current()
    assert second is not first
    assert slot.current() is second
    assert source.reads == 2


def test_an_installed_snapshot_wins_over_the_memo():
    version = [0]
    slot = SettingsSlot("t", object, version=lambda: version[0])
    derived = slot.current()
    pinned = object()
    with slot.installed(pinned):
        assert slot.current() is pinned
    assert slot.current() is derived
