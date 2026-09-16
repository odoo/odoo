import dataclasses

import pytest
from werkzeug.exceptions import BadRequest

from odoo.http._params import ParamSpec, coerce_params, get_param_specs


@dataclasses.dataclass
class Point:
    x: int
    y: int = 0


@dataclasses.dataclass
class Shape:
    name: str
    points: list[Point]
    origin: Point | None = None
    tags: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class Opaque:
    blob: bytes


ORIGIN = Point(0)


def _specs(fn):
    return get_param_specs(fn)


def test_a_dataclass_parameter_is_described_field_by_field():
    def ep(self, p: Point): ...

    spec = _specs(ep)["p"]
    assert spec.target is Point and spec.required
    assert spec.fields == {
        "x": ParamSpec(int, None, False, True),
        "y": ParamSpec(int, None, False, False),
    }


def test_a_dataclass_is_built_from_an_object_with_its_fields_coerced():
    def ep(self, p: Point): ...

    out = coerce_params({"p": {"x": "3", "y": 4}}, _specs(ep))
    assert out == {"p": Point(3, 4)}


def test_a_missing_optional_field_takes_the_dataclass_default():
    def ep(self, p: Point): ...

    assert coerce_params({"p": {"x": 1}}, _specs(ep))["p"] == Point(1, 0)


def test_nested_dataclasses_lists_and_optionals_coerce_recursively():
    def ep(self, s: Shape): ...

    out = coerce_params(
        {
            "s": {
                "name": "tri",
                "points": [{"x": "0"}, {"x": 1, "y": "2"}],
                "origin": None,
                "tags": ["a", 1],
            }
        },
        _specs(ep),
    )
    assert out["s"] == Shape("tri", [Point(0), Point(1, 2)], None, ["a", "1"])


def test_a_list_of_dataclasses_as_the_parameter_itself():
    def ep(self, pts: list[Point]): ...

    assert coerce_params({"pts": [{"x": 1}]}, _specs(ep))["pts"] == [Point(1)]
    with pytest.raises(BadRequest, match=r"pts\[0\]"):
        coerce_params({"pts": ["nope"]}, _specs(ep))


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("not an object", "must be an object"),
        ({"x": 1, "z": 2}, "unknown field"),
        ({"y": 1}, "missing required field 'x'"),
        ({"x": "abc"}, "'p.x' must be an integer"),
    ],
)
def test_a_malformed_object_is_a_400_naming_the_field(value, message):
    def ep(self, p: Point): ...

    with pytest.raises(BadRequest, match=message):
        coerce_params({"p": value}, _specs(ep))


def test_an_optional_dataclass_accepts_null_and_stays_required_when_bare():
    def ep(self, p: Point | None = None, q: Point = ORIGIN): ...

    specs = _specs(ep)
    assert specs["p"].allow_none and not specs["p"].required
    assert coerce_params({"p": None}, specs)["p"] is None
    assert not specs["q"].required


def test_a_dataclass_with_an_uncoercible_field_is_left_uncoerced():
    def ep(self, o: Opaque): ...

    assert "o" not in _specs(ep), (
        "bytes is not a wire type; the parameter passes through"
    )


def test_a_self_referencing_dataclass_does_not_recurse_forever():
    @dataclasses.dataclass
    class Node:
        value: int
        next: Node | None = None

    def ep(self, n: Node): ...

    assert "n" not in _specs(ep), "a recursive shape is declined, not looped"
