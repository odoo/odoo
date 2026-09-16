import threading
from typing import Any

from odoo.http._rpc import _restore_thread_attr


def test_restore_thread_attr_deletes_when_absent():
    sentinel = object()
    t: Any = threading.current_thread()
    if hasattr(t, "_probe_attr"):
        del t._probe_attr
    _restore_thread_attr(t, "_probe_attr", sentinel, sentinel)
    assert not hasattr(t, "_probe_attr")
    _restore_thread_attr(t, "_probe_attr", 42, sentinel)
    assert t._probe_attr == 42
    del t._probe_attr
