from odoo.libs.settings import SettingsSlot


def test_without_a_version_every_read_derives():
    reads = []
    slot = SettingsSlot("t", lambda: reads.append(1) or len(reads))
    assert slot.current() == 1
    assert slot.current() == 2


def test_with_a_version_the_snapshot_is_reused_until_the_version_moves():
    version = [0]
    reads = []
    slot = SettingsSlot(
        "t", lambda: reads.append(1) or object(), version=lambda: version[0]
    )
    first = slot.current()
    assert slot.current() is first
    assert len(reads) == 1
    version[0] += 1
    second = slot.current()
    assert second is not first
    assert slot.current() is second
    assert len(reads) == 2


def test_an_installed_snapshot_wins_over_the_memo():
    version = [0]
    slot = SettingsSlot("t", object, version=lambda: version[0])
    derived = slot.current()
    pinned = object()
    with slot.installed(pinned):
        assert slot.current() is pinned
    assert slot.current() is derived
