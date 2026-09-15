import collections
import logging
import random
import sys
from types import ModuleType
from typing import Any

import pytest

from odoo.http import _generate_routing_rules

DIAMOND = """
from odoo.http import Controller, route

class Left(Controller):
    @route("/diamond/left", auth="none")
    def left(self):
        return "left"

class Right(Controller):
    @route("/diamond/right", auth="none")
    def right(self):
        return "right"
"""

LEAF = """
from odoo.http import route
from odoo.addons.rd_sides import Left, Right

class Both(Left, Right):
    @route("/diamond/both", auth="none")
    def both(self):
        return "both"
"""

OVERLAP = """
from odoo.http import Controller, route

class Left(Controller):
    @route("/ov/left", auth="none")
    def left(self):
        return "left"

class Right(Controller):
    @route("/ov/right", auth="none")
    def right(self):
        return "right"
"""

OVERLAP_LEAVES = """
from odoo.http import route
from odoo.addons.rd_ov import Left, Right

class OnlyLeft(Left):
    @route("/ov/only-left", auth="none")
    def only_left(self):
        return "only-left"

class Shared(Left, Right):
    @route("/ov/shared", auth="none")
    def shared(self):
        return "shared"
"""

CHAIN = """
from odoo.http import Controller, route

class Parent(Controller):
    @route("/chain/parent", auth="none")
    def parent(self):
        return "parent"

class Child(Parent):
    @route()
    def parent(self):
        return "child"
"""


def _install(monkeypatch, name, source):
    module = ModuleType(f"odoo.addons.{name}")
    monkeypatch.setitem(sys.modules, f"odoo.addons.{name}", module)
    exec(compile(source, f"<{name}>", "exec"), module.__dict__)  # noqa: S102  the source is this file's own fixture, not input
    return module


@pytest.fixture
def diamond(monkeypatch):
    _install(monkeypatch, "rd_sides", DIAMOND)
    _install(monkeypatch, "rd_leaf", LEAF)
    yield


@pytest.fixture
def overlap(monkeypatch):
    _install(monkeypatch, "rd_ov", OVERLAP)
    _install(monkeypatch, "rd_ov_leaves", OVERLAP_LEAVES)
    yield


@pytest.fixture
def chain(monkeypatch):
    _install(monkeypatch, "rd_chain", CHAIN)
    yield


def _cls(name):
    return type(name, (), {})


def _urls(mods):
    return collections.Counter(url for url, _ in _generate_routing_rules(mods, False))


def test_a_diamond_leaf_yields_each_route_once(diamond):
    urls = _urls(["rd_sides", "rd_leaf"])
    assert urls == {
        "/diamond/left": 1,
        "/diamond/right": 1,
        "/diamond/both": 1,
    }


def test_the_diamond_leafs_own_route_is_still_reachable(diamond):
    endpoints = dict(_generate_routing_rules(["rd_sides", "rd_leaf"], False))
    assert endpoints["/diamond/both"].routing["auth"] == "none"


def test_a_diamond_without_its_leaf_installed_keeps_both_sides(diamond):
    assert _urls(["rd_sides"]) == {"/diamond/left": 1, "/diamond/right": 1}


def test_a_plain_override_chain_is_unaffected(chain):
    urls = _urls(["rd_chain"])
    assert urls == {"/chain/parent": 1}


def test_an_override_chain_still_resolves_to_the_child(chain):
    endpoints = dict(_generate_routing_rules(["rd_chain"], False))
    endpoint = endpoints["/chain/parent"]
    controller: Any = endpoint.func.__self__
    assert controller.parent().get_data() == b"child"


def test_overlapping_leaf_sets_are_fused_into_one_tree(overlap):
    assert _urls(["rd_ov", "rd_ov_leaves"]) == {
        "/ov/left": 1,
        "/ov/right": 1,
        "/ov/only-left": 1,
        "/ov/shared": 1,
    }


def test_the_fused_tree_carries_every_leaf(overlap):
    from odoo.http.controller import _get_controllers

    controllers = list(_get_controllers(["rd_ov", "rd_ov_leaves"]))
    assert len(controllers) == 1
    mro_names = {cls.__name__ for cls in type(controllers[0]).mro()}
    assert {"OnlyLeft", "Shared", "Left", "Right"} <= mro_names


def test_fusion_is_transitive():
    from odoo.http.controller import _group_controller_trees

    A = _cls("A")
    B = _cls("B")
    C = _cls("C")
    L1 = _cls("L1")
    L2 = _cls("L2")
    L3 = _cls("L3")

    grouped = _group_controller_trees([(A, [L1, L2]), (C, [L3]), (B, [L2, L3])])
    assert len(grouped) == 1
    top, leaves = grouped[0]
    assert top is A
    assert set(leaves) == {L1, L2, L3}


def test_unrelated_trees_stay_apart():
    from odoo.http.controller import _group_controller_trees

    A = _cls("A")
    B = _cls("B")
    L1 = _cls("L1")
    L2 = _cls("L2")

    grouped = _group_controller_trees([(A, [L1]), (B, [L2])])
    assert [(top, list(leaves)) for top, leaves in grouped] == [(A, [L1]), (B, [L2])]


def test_a_tree_with_no_leaf_contributes_nothing():
    from odoo.http.controller import _group_controller_trees

    A = _cls("A")
    L1 = _cls("L1")

    assert _group_controller_trees([(A, []), (A, [L1])]) == [(A, [L1])]


def test_leaf_order_survives_fusion():
    from odoo.http.controller import _group_controller_trees

    A = _cls("A")
    B = _cls("B")
    L1 = _cls("L1")
    L2 = _cls("L2")
    L3 = _cls("L3")

    grouped = _group_controller_trees([(A, [L1, L2]), (B, [L2, L3])])
    assert grouped == [(A, [L1, L2, L3])]


def _gen_hierarchy(rng, tag):
    n_base = rng.randint(1, 4)
    base_src = ["from odoo.http import Controller, route", ""]
    declared: dict[str, tuple[str, str]] = {}
    methods: list[tuple[str, str]] = []
    for i in range(n_base):
        cls = f"B{i}"
        body = []
        for j in range(rng.randint(1, 3)):
            meth, url = f"m{i}_{j}", f"/{tag}/b{i}/{j}"
            declared[url] = (cls, meth)
            methods.append((cls, meth))
            body.append(
                f'    @route("{url}", auth="none")\n'
                f'    def {meth}(self):\n        return "{cls}.{meth}"\n'
            )
        base_src.append(f"class {cls}(Controller):\n" + "\n".join(body))

    names = [f"B{i}" for i in range(n_base)]
    der_src = [
        "from odoo.http import route",
        f"from odoo.addons.{tag}_base import " + ", ".join(names),
        "",
    ]
    overrides: dict[str, str] = {}
    derived: list[str] = []
    ancestors: dict[str, set[str]] = {n: set() for n in names}
    for k in range(rng.randint(0, 4)):
        cls = f"D{k}"
        pool = names + derived
        chosen = rng.sample(pool, rng.randint(1, min(2, len(pool))))
        chosen = [
            c for c in chosen if not any(c in ancestors[o] for o in chosen if o != c)
        ]
        bases = sorted(chosen, key=pool.index)
        body = []
        candidates = [
            (c, m)
            for (c, m) in methods
            if (c in bases or any(c in b for b in bases)) and m not in overrides
        ]
        if candidates and rng.random() < 0.7:
            _, meth = rng.choice(candidates)
            body.append(
                "    @route(auth='none')\n"
                f'    def {meth}(self):\n        return "{cls}.{meth}"\n'
            )
            overrides[meth] = cls
        if rng.random() < 0.6:
            meth, url = f"n{k}", f"/{tag}/d{k}"
            declared[url] = (cls, meth)
            methods.append((cls, meth))
            body.append(
                f'    @route("{url}", auth="none")\n'
                f'    def {meth}(self):\n        return "{cls}.{meth}"\n'
            )
        if not body:
            body.append("    pass\n")
        der_src.append(f"class {cls}({', '.join(bases)}):\n" + "\n".join(body))
        ancestors[cls] = set(bases).union(*(ancestors[b] for b in bases))
        derived.append(cls)

    return "\n".join(base_src), "\n".join(der_src), declared, overrides


@pytest.mark.parametrize("seed", range(40))
def test_a_random_hierarchy_yields_every_route_once_and_the_deepest_override(
    seed, monkeypatch
):
    from odoo.http.controller import Controller

    rng = random.Random(seed)
    tag = f"rdfuzz{seed}"
    base_src, der_src, declared, overrides = _gen_hierarchy(rng, tag)
    try:
        _install(monkeypatch, f"{tag}_base", base_src)
        _install(monkeypatch, f"{tag}_der", der_src)
    except TypeError as exc:  # pragma: no cover - generator hygiene
        if "method resolution order" in str(exc):
            pytest.skip("the generator emitted an invalid MRO")
        raise
    try:
        rules = list(_generate_routing_rules([f"{tag}_base", f"{tag}_der"], False))

        assert collections.Counter(url for url, _ in rules) == dict.fromkeys(
            declared, 1
        )

        for url, endpoint in rules:
            _, meth = declared[url]
            if meth in overrides:
                body = endpoint().get_data(as_text=True)
                assert body.startswith(overrides[meth] + "."), url
    finally:
        for name in (f"{tag}_base", f"{tag}_der"):
            Controller.children_classes.pop(name, None)


MRO_BASES = """
from odoo.http import Controller, route

class B0(Controller):
    @route("/mro/b0", auth="none")
    def b0(self):
        return "b0"

class B1(Controller):
    @route("/mro/b1", auth="none")
    def b1(self):
        return "b1"

class Innocent(Controller):
    @route("/mro/innocent", auth="none")
    def innocent(self):
        return "innocent"
"""

MRO_ADDON_A = """
from odoo.http import route
from odoo.addons.mro_base import B0, B1

class DA(B0, B1):
    @route("/mro/da", auth="none")
    def da(self):
        return "da"
"""

MRO_ADDON_B = """
from odoo.http import route
from odoo.addons.mro_base import B0, B1

class DB(B1, B0):
    @route("/mro/db", auth="none")
    def db(self):
        return "db"
"""


@pytest.fixture
def incompatible_orders(monkeypatch):
    _install(monkeypatch, "mro_base", MRO_BASES)
    _install(monkeypatch, "mro_a", MRO_ADDON_A)
    _install(monkeypatch, "mro_b", MRO_ADDON_B)
    yield
    from odoo.http.controller import Controller

    for name in ("mro_base", "mro_a", "mro_b"):
        Controller.children_classes.pop(name, None)


def test_controllers_extending_shared_bases_in_opposite_orders_cost_only_themselves(
    incompatible_orders, caplog
):
    with caplog.at_level(logging.ERROR, logger="odoo.http.routing"):
        urls = _urls(["mro_base", "mro_a", "mro_b"])

    assert "/mro/innocent" in urls, "an unrelated controller must survive"
    assert "/mro/da" not in urls
    assert "/mro/db" not in urls

    message = "\n".join(r.getMessage() for r in caplog.records)
    assert "mro_a.DA" in message and "mro_b.DB" in message
    assert "incompatible orders" in message
