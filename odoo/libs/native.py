import os
import zlib
from collections.abc import Mapping
from pathlib import Path

__all__ = ["assert_fresh", "assert_optimised", "native_required", "source_crc"]

SKIP_ENV = "ODOO_SKIP_RUST_FRESHNESS_CHECK"

ALLOW_DEBUG_ENV = "ODOO_ALLOW_DEBUG_RUST"


WORKSPACE_INPUTS = ("Cargo.lock", "Cargo.toml")


def source_crc(crate: Path) -> str:
    sources = (crate / "src").rglob("*.rs", recurse_symlinks=True)
    inputs = sorted(
        [
            (path.relative_to(crate).as_posix(), path)
            for path in (crate / "Cargo.toml", *sources)
        ]
        + [
            (f"../{name}", crate.parent / name)
            for name in WORKSPACE_INPUTS
            if (crate.parent / name).is_file()
        ],
        key=lambda pair: pair[0],
    )
    blob = b"".join(
        rel.encode() + b"\0" + path.read_bytes() + b"\0" for rel, path in inputs
    )
    return f"{zlib.crc32(blob):08x}"


def assert_fresh(module: object, crate: Path, *, rebuild_hint: str = "") -> None:
    if not crate.is_dir() or os.environ.get(SKIP_ENV):
        return

    built = getattr(module, "__source_crc__", None)
    current = source_crc(crate)
    if built == current:
        return

    name = getattr(module, "__name__", str(module))
    was = "predates the build script" if built is None else f"built from {built}"
    raise RuntimeError(
        f"The installed {name!r} extension is stale: it was {was}, but the "
        f"crate in this checkout is {current}. The pure-Python fallbacks step in "
        f"only when the extension is ABSENT; a stale one is imported and gives "
        f"wrong results rather than slow ones. Rebuild it:\n"
        f"    maturin build --release --manifest-path "
        f"{crate.name and f'crates/{crate.name}/Cargo.toml'} --out dist\n"
        f"    pip install --force-reinstall --no-deps dist/{name}-*.whl\n"
        f"(or `maturin develop --release` in {crate}.)"
        f"{rebuild_hint}"
        f" Set {SKIP_ENV}=1 to bypass this check."
    )


REQUIRE_ENV = "ODOO_REQUIRE_NATIVE"


def native_required(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    value = env.get(REQUIRE_ENV, env.get("CI", ""))
    return value.strip().lower() not in ("", "0", "false", "no")


def assert_optimised(module: object) -> None:
    if os.environ.get(ALLOW_DEBUG_ENV):
        return
    profile = getattr(module, "__profile__", None)
    if profile == "release":
        return

    name = getattr(module, "__name__", str(module))
    raise RuntimeError(
        f"The installed {name!r} extension was built with the {profile!r} "
        f"profile. It has no pure-Python fallback and exists only to be faster; "
        f"unoptimised, four of its exports are slower than the code they "
        f"replace. `maturin develop` defaults to this profile — pass --release:"
        f"\n    maturin develop --release\n"
        f"Set {ALLOW_DEBUG_ENV}=1 to run on it anyway (attaching a debugger)."
    )
