import dataclasses
from typing import Annotated, Literal, NotRequired, Required, TypedDict

import pytest
from werkzeug.exceptions import BadRequest

from odoo.http._params import Discriminator, Range, coerce_params, get_param_specs


def test_foreign_annotated_metadata_still_coerces_the_base_type():
    def ep(self, n: Annotated[int, "a note for the reader"]): ...

    specs = get_param_specs(ep)
    assert specs["n"].target is int
    assert coerce_params({"n": "7"}, specs) == {"n": 7}


def test_two_range_markers_bound_both_ends():
    def ep(self, n: Annotated[int, Range(ge=0), Range(le=10)]): ...

    specs = get_param_specs(ep)
    constraints = specs["n"].constraints
    assert constraints is not None
    assert (constraints.ge, constraints.le) == (0, 10)
    with pytest.raises(BadRequest):
        coerce_params({"n": "11"}, specs)
    with pytest.raises(BadRequest):
        coerce_params({"n": "-1"}, specs)


def test_a_range_on_a_string_is_refused_at_build_not_a_500_at_request():
    def ep(self, s: Annotated[str, Range(ge=1)]): ...

    with pytest.raises(TypeError, match="Range bounds a number"):
        get_param_specs(ep)


class Line(TypedDict):
    sku: str
    qty: NotRequired[int]


class Patch(TypedDict, total=False):
    id: Required[int]
    note: str


def test_required_and_not_required_typeddict_keys_are_coerced():
    def ep(self, line: Line, patch: Patch): ...

    specs = get_param_specs(ep)
    line_fields, patch_fields = specs["line"].fields, specs["patch"].fields
    assert line_fields is not None and patch_fields is not None
    assert line_fields["qty"].target is int
    assert not line_fields["qty"].required
    assert patch_fields["id"].required
    coerced = coerce_params(
        {"line": {"sku": "a", "qty": "2"}, "patch": {"id": "3"}}, specs
    )
    assert coerced == {"line": {"sku": "a", "qty": 2}, "patch": {"id": 3}}
    with pytest.raises(BadRequest):
        coerce_params({"line": {"sku": "a"}, "patch": {"note": "x"}}, specs)


@dataclasses.dataclass
class Node:
    name: str
    children: list[Node] = dataclasses.field(default_factory=list)


def test_a_recursive_dataclass_is_left_uncoerced_not_half_built():
    def ep(self, node: Node): ...

    assert "node" not in get_param_specs(ep)


@dataclasses.dataclass
class Seeded:
    value: int
    seed: dataclasses.InitVar[int]


def test_a_dataclass_with_an_init_var_is_left_uncoerced():
    def ep(self, s: Seeded): ...

    assert "s" not in get_param_specs(ep)


@dataclasses.dataclass
class Positive:
    n: int

    def __post_init__(self):
        if self.n <= 0:
            raise ValueError("n must be positive")


def test_a_constructor_refusal_is_a_bad_request():
    def ep(self, p: Positive): ...

    specs = get_param_specs(ep)
    with pytest.raises(BadRequest, match="n must be positive"):
        coerce_params({"p": {"n": 0}}, specs)


@dataclasses.dataclass
class Card:
    kind: Literal["card"]
    number: str


@dataclasses.dataclass
class Wire:
    kind: Literal["wire"]
    iban: str


@pytest.mark.parametrize("tag", [["card"], {"card": 1}, True])
def test_a_tag_that_is_not_a_scalar_is_a_bad_request(tag):
    def ep(self, pay: Annotated[Card | Wire, Discriminator("kind")]): ...

    specs = get_param_specs(ep)
    with pytest.raises(BadRequest):
        coerce_params({"pay": {"kind": tag, "number": "4"}}, specs)
