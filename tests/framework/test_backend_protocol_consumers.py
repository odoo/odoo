"""`StorageBackend` has an implementation outside this repository.

`odoo-rust-orm/engine-py/python/rust_backend.py` implements this protocol, and
its addon is the fifth entry of the workspace `addons_path` and sits in
`server_wide_modules`, so it loads in every local run. It is in no gate, and a
grep of the four Odoo checkouts does not reach it -- which is how a `search_raw`
removal disabled its search path on 2026-09-21.

This is the cheap standing check: every call the protocol permits is one that
implementation accepts. It skips where the repository is absent, so a checkout
without it is unaffected; where it is present, an ordinary Tier-2 run catches a
signature change at the moment it is made rather than when a query runs.

Measured when this was written: 25 protocol methods, 0 incompatible, and the
real surface is the four the engine implements natively -- `create_rows`,
`update_rows`, `search` and `search_raw`. The other 21 are `*args, **kwargs`
wrappers that forward to the delegate and cannot break.
"""

import ast
import pathlib

import pytest

import odoo.orm.runtime.backend as backend_module

PROTOCOL = pathlib.Path(backend_module.__file__)
ENGINE = (
    PROTOCOL.resolve().parents[4]
    / "odoo-rust-orm"
    / "engine-py"
    / "python"
    / "rust_backend.py"
)


def _spec(fn: ast.FunctionDef) -> dict:
    a = fn.args
    positional = [p.arg for p in a.posonlyargs + a.args]
    return {
        "pos": positional,
        "kwonly": {p.arg for p in a.kwonlyargs},
        "kwonly_required": {
            p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults, strict=True) if d is None
        },
        "star": a.vararg is not None,
        "starstar": a.kwarg is not None,
        "n_required_pos": len(positional) - len(a.defaults),
    }


def _methods(path: pathlib.Path, only: set[str] | None = None) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef) and (only is None or node.name in only):
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and not child.name.startswith(
                    "__"
                ):
                    found.setdefault(child.name, _spec(child))
    return found


def _why_incompatible(protocol: dict, impl: dict) -> str:
    if impl["star"] and impl["starstar"]:
        return ""
    wanted, given = protocol["pos"], impl["pos"]
    if not impl["star"]:
        if len(given) < len(wanted):
            return f"takes {len(given)} positional, the protocol passes {len(wanted)}"
        if given[: len(wanted)] != wanted:
            return f"positional names differ: {wanted} vs {given[: len(wanted)]}"
        if impl["n_required_pos"] > len(wanted):
            return "requires a positional the protocol never passes"
    if not impl["starstar"]:
        rejected = protocol["kwonly"] - impl["kwonly"] - set(given)
        if rejected:
            return f"rejects keyword(s) the protocol passes: {sorted(rejected)}"
        demanded = impl["kwonly_required"] - protocol["kwonly"]
        if demanded:
            return f"requires keyword(s) the protocol never passes: {sorted(demanded)}"
    return ""


@pytest.fixture(scope="module")
def engine() -> dict[str, dict]:
    if not ENGINE.is_file():
        pytest.skip(f"the rust engine is not checked out beside this repo ({ENGINE})")
    return _methods(ENGINE)


@pytest.fixture(scope="module")
def protocol() -> dict[str, dict]:
    declared = _methods(PROTOCOL, {"StorageBackend"})
    assert declared, "StorageBackend no longer parses as a class here"
    return declared


class TestTheOutOfTreeBackendStillFitsTheProtocol:
    def test_it_accepts_every_call_the_protocol_permits(self, protocol, engine):
        broken = {
            name: (
                "not implemented"
                if name not in engine
                else _why_incompatible(spec, engine[name])
            )
            for name, spec in protocol.items()
            if name not in engine or _why_incompatible(spec, engine[name])
        }
        assert not broken, (
            f"the out-of-tree StorageBackend no longer fits this protocol: "
            f"{broken}. It loads in every local run via server_wide_modules, "
            f"and no grep of the Odoo checkouts reaches it"
        )

    def test_the_native_surface_is_exactly_these_four(self, protocol, engine):
        """The small surface a protocol change can actually break.

        A `*args, **kwargs` wrapper forwards whatever it is given, so it
        survives any signature change to the method it implements; only a
        method written out with real parameters can break. Twenty-one of the
        engine's implementations are wrappers, which is *why* the exposure is
        four methods rather than twenty-five.

        Asserted as an equality and not a superset, because the number that
        matters is how many there are. A wrapper narrowed to an explicit
        signature silently joins this set: the compatibility test above would
        still catch it the day it breaks, and nobody would have been told the
        blast radius of editing `StorageBackend` had grown before then.
        """
        native = {
            name
            for name, spec in engine.items()
            if name in protocol and not (spec["star"] and spec["starstar"])
        }
        assert native == {"create_rows", "update_rows", "search", "search_raw"}, (
            f"the engine's native implementation surface changed to {sorted(native)}. "
            f"A method that stopped delegating can now break on a signature "
            f"change; one that started delegating cannot. Either way the "
            f"protocol's blast radius moved and this pin should move with it"
        )

    def test_the_protocol_parses_as_more_than_a_stub(self, protocol):
        """A positive control: an empty parse would pass both tests above."""
        assert len(protocol) > 15, (
            f"only {len(protocol)} StorageBackend methods parsed; the tests "
            f"above would pass against an empty protocol"
        )
