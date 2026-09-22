import io
from pathlib import Path

import pytest

from odoo.cli.stubs import _write_stubs


def test_a_reader_of_the_previous_stub_keeps_a_complete_snapshot(tmp_path):
    target = tmp_path / "odoo_registry_stubs.pyi"
    target.write_text("old complete registry")
    target.chmod(0o640)
    with target.open() as reader:
        _write_stubs(target, "new complete registry")
        assert reader.read() == "old complete registry"
    assert target.read_text() == "new complete registry"
    assert target.stat().st_mode & 0o777 == 0o640
    assert list(tmp_path.iterdir()) == [target]


def test_a_partial_write_failure_preserves_the_previous_stub(tmp_path, monkeypatch):
    target = tmp_path / "odoo_registry_stubs.pyi"
    target.write_text("old complete registry")
    original_open = io.open

    class BrokenWriter:
        def __init__(self, stream):
            self.stream = stream

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def write(self, text):
            self.stream.write(text[:4])
            self.stream.flush()
            raise OSError("injected disk failure")

    def interrupted_open(*args, **kwargs):
        return BrokenWriter(original_open(*args, **kwargs))

    with monkeypatch.context() as patch:
        patch.setattr(io, "open", interrupted_open)
        with pytest.raises(OSError, match="injected disk failure"):
            _write_stubs(target, "new complete registry")
    assert target.read_text() == "old complete registry"
    assert list(tmp_path.iterdir()) == [target]


def test_a_failed_publication_cleans_up_temporary_files(tmp_path, monkeypatch):
    target = tmp_path / "odoo_registry_stubs.pyi"
    target.write_text("old complete registry")

    def fail_replace(self, destination):
        raise OSError("injected rename failure")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="injected rename failure"):
        _write_stubs(target, "new complete registry")
    assert target.read_text() == "old complete registry"
    assert list(tmp_path.iterdir()) == [target]


def test_a_new_stub_uses_normal_file_creation_permissions(tmp_path):
    control = tmp_path / "ordinary.pyi"
    control.write_text("ordinary file")
    target = tmp_path / "odoo_registry_stubs.pyi"
    _write_stubs(target, "new complete registry")
    assert target.stat().st_mode & 0o777 == control.stat().st_mode & 0o777
