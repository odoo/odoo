import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

# Bump when compiler semantics change without a corresponding source/stub change.
_SOURCE_KEY_VERSION = "3"

# the by-source key: what esbuild was given, stored on the published build so a
# process that has not compiled yet can serve the bundle another one compiled

DEFAULT_VARIANT = "default"


def variant_key(
    assets_params: Mapping[str, Any] | None = None,
    *,
    page_scope: Iterable[str] = (),
    standalone: bool = False,
) -> str:
    # what selects a different build of one bundle besides its sources; two
    # variants are published side by side and never supersede each other
    parts = [
        f"{key}={value}"
        for key, value in sorted((assets_params or {}).items())
        if value not in (None, False, "")
    ]
    if page_scope:
        parts.append("page=" + "+".join(sorted(page_scope)))
    if standalone:
        parts.append("standalone")
    return ";".join(parts) or DEFAULT_VARIANT


def source_key(
    bundle: str,
    native_modules: Iterable[Any],
    dynamic_child_specs: Iterable[str] | None,
    secondary_stubs: dict[str, str],
    exported_specs: Iterable[str] | None,
    target: str,
    source_maps: str,
) -> str:
    digest = hashlib.sha256()
    for part in (
        _SOURCE_KEY_VERSION,
        bundle,
        target,
        source_maps,
        ",".join(sorted(dynamic_child_specs or ())),
        ",".join(sorted(exported_specs or ())),
    ):
        digest.update(part.encode())
        digest.update(b"\0")
    for spec in sorted(secondary_stubs):
        digest.update(spec.encode())
        digest.update(secondary_stubs[spec].encode())
        digest.update(b"\0")
    for asset in native_modules:
        digest.update((asset.module_path or asset.url or "").encode())
        digest.update(b"\0")
        raw = asset.raw_content
        digest.update(raw.encode() if isinstance(raw, str) else raw)
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def sidecar_urls(url: str) -> dict[str, str]:
    return {
        "metafile": url.removesuffix(".esm.js") + ".meta.json",
        "sourcemap": url + ".map",
    }


def group_source_key(
    group: str,
    entries: dict[str, Iterable[Any]],
    templates: dict[str, str],
    parent_specs: Iterable[str],
    secondary_stubs: dict[str, str],
    target: str,
    source_maps: str,
) -> str:
    digest = hashlib.sha256()
    for part in (
        _SOURCE_KEY_VERSION,
        group,
        target,
        source_maps,
        ",".join(sorted(parent_specs)),
    ):
        digest.update(part.encode())
        digest.update(b"\0")
    for name in sorted(templates):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(templates[name].encode())
        digest.update(b"\0")
    for spec in sorted(secondary_stubs):
        digest.update(spec.encode())
        digest.update(secondary_stubs[spec].encode())
        digest.update(b"\0")
    for name in sorted(entries):
        digest.update(name.encode())
        digest.update(b"\0")
        for asset in entries[name]:
            digest.update((asset.module_path or asset.url or "").encode())
            digest.update(b"\0")
            raw = asset.raw_content
            digest.update(raw.encode() if isinstance(raw, str) else raw)
            digest.update(b"\0")
    return digest.hexdigest()[:16]
