import hashlib
import json
from collections.abc import Callable, Iterable
from typing import Any

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

# Bump when compiler semantics change without a corresponding source/stub change.
_SOURCE_KEY_VERSION = "2"

# the by-source index: one small row beside a compiled bundle, keyed on what
# esbuild was given, so a process that has not compiled yet can serve the
# bundle another one compiled


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


def index_url(bundle: str, key: str) -> str:
    return f"/web/assets/esm/by-source/{key}/{bundle}.json"


def index_row(bundle: str, key: str, url: str, metafile: bool, sourcemap: bool) -> dict:
    return {
        "name": f"{bundle}.by-source.json",
        "mimetype": "application/json",
        "res_model": "ir.ui.view",
        "res_id": False,
        "type": "binary",
        "public": True,
        "raw": json.dumps(
            {"url": url, "metafile": metafile, "sourcemap": sourcemap}
        ).encode("utf-8"),
        "url": index_url(bundle, key),
    }


def sidecar_urls(url: str) -> dict[str, str]:
    return {
        "metafile": url.removesuffix(".esm.js") + ".meta.json",
        "sourcemap": url + ".map",
    }


def resolve_index(
    read: Callable[[str], bytes | None], bundle: str, key: str
) -> tuple[str, str, str | None, str | None] | None:
    # `read` answers the raw bytes of a generated asset at a url, or None;
    # the result is (url, code, metafile, sourcemap), or None when any part
    # the index promises is missing
    pointer_raw = read(index_url(bundle, key))
    if pointer_raw is None:
        _debug.logic("esm_index.miss", bundle=bundle, key=key, missing="pointer")
        return None
    try:
        pointer = json.loads(pointer_raw.decode("utf-8"))
        url = pointer["url"]
    except ValueError, KeyError, AttributeError:
        _debug.logic("esm_index.miss", bundle=bundle, key=key, missing="malformed")
        return None
    code = read(url)
    if code is None:
        _debug.logic("esm_index.miss", bundle=bundle, key=key, missing="code")
        return None
    parts: dict[str, str | None] = {"metafile": None, "sourcemap": None}
    for name, sidecar_url in sidecar_urls(url).items():
        if pointer.get(name):
            raw = read(sidecar_url)
            if raw is None:
                _debug.logic("esm_index.miss", bundle=bundle, key=key, missing=name)
                return None
            parts[name] = raw.decode("utf-8")
    _debug.logic(
        "esm_index.hit",
        bundle=bundle,
        key=key,
        url=url,
        metafile=parts["metafile"] is not None,
        sourcemap=parts["sourcemap"] is not None,
    )
    return url, code.decode("utf-8"), parts["metafile"], parts["sourcemap"]
