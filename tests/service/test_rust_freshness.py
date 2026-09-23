import zlib

import odoo_rust
import pytest

from odoo.libs.native import assert_fresh, assert_optimised, source_crc

from .._pg import repo_root

CRATES = repo_root() / "crates"
CRATE = CRATES / "odoo_rust"

needs_crate_sources = pytest.mark.skipif(
    not CRATE.is_dir(), reason="no crate sources — an installed deployment"
)


@needs_crate_sources
def test_the_installed_extension_matches_the_crate():
    assert odoo_rust.__source_crc__ == source_crc(CRATE), (
        "the installed odoo_rust predates the crate in this checkout — rebuild "
        "it (maturin build --release ...), or see odoo/init.py for the message"
    )


@needs_crate_sources
def test_every_native_crate_is_covered_by_a_freshness_check():
    crates = {p.name for p in CRATES.iterdir() if (p / "Cargo.toml").is_file()}
    extensions = crates - {"odoo_build"}
    assert extensions == {"odoo_rust", "odoo_lint"}, (
        f"native extension crates are now {sorted(extensions)}; each needs an "
        f"assert_fresh() at its import site, and this list updated"
    )
    for name in sorted(extensions):
        assert "stamp_build_identity" in (CRATES / name / "build.rs").read_text(), (
            f"{name}/build.rs does not stamp a build identity, so nothing can "
            f"detect a stale or unoptimised build of it"
        )


def test_assert_fresh_raises_on_a_mismatch_and_passes_on_a_match(tmp_path, monkeypatch):
    monkeypatch.delenv("ODOO_SKIP_RUST_FRESHNESS_CHECK", raising=False)

    class Module:
        __name__ = "pretend_ext"
        __source_crc__ = "deadbeef"

    crate = tmp_path / "pretend_ext"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text("[package]\n")
    (crate / "src" / "lib.rs").write_text("// lib\n")

    module = Module()
    with pytest.raises(RuntimeError, match="stale"):
        assert_fresh(module, crate)

    module.__source_crc__ = source_crc(crate)
    assert_fresh(module, crate)

    assert_fresh(Module(), tmp_path / "absent")


def test_the_fingerprint_covers_every_build_input(tmp_path):
    copy = tmp_path / "odoo_rust"
    copy.mkdir()
    (copy / "src").mkdir()
    (copy / "Cargo.toml").write_text("[package]\nname = 'x'\n")
    (copy / "src" / "lib.rs").write_text("// lib\n")
    (copy / "src" / "clone.rs").write_text("// clone\n")

    baseline = source_crc(copy)

    for target, edited in (
        (copy / "src" / "clone.rs", "// clone edited\n"),
        (copy / "Cargo.toml", "[package]\nname = 'x'\nversion = '2'\n"),
    ):
        original = target.read_text()
        target.write_text(edited)
        assert source_crc(copy) != baseline, f"{target.name} is not hashed"
        target.write_text(original)

    assert source_crc(copy) == baseline, "restoring the sources must restore the crc"

    (copy / "src" / "added.rs").write_text("// added\n")
    assert source_crc(copy) != baseline, "a new source file is not hashed"


def test_the_fingerprint_covers_the_resolved_dependency_versions(tmp_path):
    workspace = tmp_path / "crates"
    crate = workspace / "odoo_rust"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text("[package]\n")
    (crate / "src" / "lib.rs").write_text("// lib\n")

    without_lock = source_crc(crate)

    lock = workspace / "Cargo.lock"
    lock.write_text('[[package]]\nname = "pyo3"\nversion = "0.29.2"\n')
    with_lock = source_crc(crate)
    assert with_lock != without_lock, "the lock file is not hashed"

    lock.write_text('[[package]]\nname = "pyo3"\nversion = "0.29.3"\n')
    assert source_crc(crate) != with_lock, (
        "a resolved dependency version change does not move the fingerprint"
    )


def test_the_fingerprint_covers_the_workspace_manifest(tmp_path):
    workspace = tmp_path / "crates"
    crate = workspace / "odoo_rust"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text("[package]\nedition.workspace = true\n")
    (crate / "src" / "lib.rs").write_text("// lib\n")

    without_manifest = source_crc(crate)

    manifest = workspace / "Cargo.toml"
    manifest.write_text('[workspace.package]\nedition = "2021"\n')
    with_manifest = source_crc(crate)
    assert with_manifest != without_manifest, "the workspace manifest is not hashed"

    manifest.write_text('[workspace.package]\nedition = "2024"\n')
    assert source_crc(crate) != with_manifest, (
        "an inherited edition change does not move the fingerprint"
    )


def test_the_fingerprint_follows_a_symlinked_source_directory(tmp_path):
    crate = tmp_path / "crate"
    (crate / "src").mkdir(parents=True)
    (crate / "Cargo.toml").write_text("[package]\n")
    (crate / "src" / "lib.rs").write_text("// lib\n")
    shared = tmp_path / "shared"
    shared.mkdir()
    (shared / "helpers.rs").write_text("// v1\n")
    (crate / "src" / "shared").symlink_to(shared, target_is_directory=True)

    before = source_crc(crate)
    (shared / "helpers.rs").write_text("// v2\n")
    assert source_crc(crate) != before, (
        "cargo compiles through the link, so the fingerprint must read it too"
    )


def test_a_debug_build_is_refused_by_name(monkeypatch):
    class Module:
        __name__ = "pretend_ext"
        __profile__ = "debug"

    monkeypatch.delenv("ODOO_ALLOW_DEBUG_RUST", raising=False)
    module = Module()
    with pytest.raises(RuntimeError, match="--release"):
        assert_optimised(module)

    module.__profile__ = "release"
    assert_optimised(module)

    del Module.__profile__
    with pytest.raises(RuntimeError, match="--release"):
        assert_optimised(Module())

    monkeypatch.setenv("ODOO_ALLOW_DEBUG_RUST", "1")
    debug = Module()
    debug.__profile__ = "debug"
    assert_optimised(debug)


def test_the_installed_extension_is_optimised():
    assert_optimised(odoo_rust)


def test_the_fingerprint_does_not_depend_on_where_the_checkout_lives(tmp_path):
    here, elsewhere = (
        tmp_path / "a" / "crate",
        tmp_path / "b" / "some" / "deeper" / "crate",
    )
    for root in (here, elsewhere):
        (root / "src").mkdir(parents=True)
        (root / "Cargo.toml").write_text("[package]\n")
        (root / "src" / "lib.rs").write_text("// lib\n")

    assert source_crc(here) == source_crc(elsewhere)


def test_python_reproduces_the_rust_crc32_parameters():
    assert zlib.crc32(b"123456789") == 0xCBF43926


def test_a_nul_delimiter_keeps_filenames_from_bleeding_together(tmp_path):
    first, second = tmp_path / "one", tmp_path / "two"
    for root in (first, second):
        (root / "src").mkdir(parents=True)
        (root / "Cargo.toml").write_text("")

    (first / "src" / "ab.rs").write_text("c")
    (second / "src" / "a.rs").write_text("bc")

    assert source_crc(first) != source_crc(second)
