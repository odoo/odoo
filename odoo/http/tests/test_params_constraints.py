import enum
from typing import Annotated, Literal, TypedDict

import pytest
from werkzeug.exceptions import BadRequest

from odoo.http._params import Pattern, Range, coerce_params, get_param_specs


class Color(enum.Enum):
    RED = "red"
    BLUE = "blue"


class Level(enum.IntEnum):
    LOW = 1
    HIGH = 3


class Page(TypedDict):
    number: Annotated[int, Range(ge=1)]
    size: int


class Filters(TypedDict, total=False):
    q: str
    page: Page


def _specs(fn):
    return get_param_specs(fn)


def test_literal_choices_coerce_and_refuse():
    def ep(self, order: Literal["asc", "desc"] = "asc"): ...

    specs = _specs(ep)
    assert specs["order"].constraints.choices == ("asc", "desc")
    assert coerce_params({"order": "desc"}, specs) == {"order": "desc"}
    with pytest.raises(BadRequest, match="must be one of"):
        coerce_params({"order": "sideways"}, specs)


def test_integer_literals_coerce_from_query_strings():
    def ep(self, limit: Literal[10, 50, 100]): ...

    assert coerce_params({"limit": "50"}, _specs(ep)) == {"limit": 50}
    with pytest.raises(BadRequest):
        coerce_params({"limit": "51"}, _specs(ep))


def test_an_enum_is_built_from_its_value():
    def ep(self, color: Color, level: Level = Level.LOW): ...

    out = coerce_params({"color": "blue", "level": "3"}, _specs(ep))
    assert out == {"color": Color.BLUE, "level": Level.HIGH}
    with pytest.raises(BadRequest, match="must be one of"):
        coerce_params({"color": "green"}, _specs(ep))


def test_ranges_and_patterns_are_checked_after_coercion():
    def ep(
        self,
        n: Annotated[int, Range(ge=1, le=10)],
        code: Annotated[str, Pattern(r"[A-Z]{3}")] = "ABC",
        ratio: Annotated[float, Range(le=1.0)] | None = None,
    ): ...

    specs = _specs(ep)
    assert coerce_params({"n": "10", "code": "XYZ", "ratio": None}, specs) == {
        "n": 10,
        "code": "XYZ",
        "ratio": None,
    }
    with pytest.raises(BadRequest, match=">= 1"):
        coerce_params({"n": 0}, specs)
    with pytest.raises(BadRequest, match="<= 10"):
        coerce_params({"n": 11}, specs)
    with pytest.raises(BadRequest, match="must match"):
        coerce_params({"n": 5, "code": "abc"}, specs)
    with pytest.raises(BadRequest, match=r"<= 1\.0"):
        coerce_params({"n": 5, "ratio": "1.5"}, specs)


def test_a_typed_dict_is_an_object_with_required_and_optional_keys():
    def ep(self, filters: Filters): ...

    specs = _specs(ep)
    assert specs["filters"].fields["q"].required is False
    assert specs["filters"].fields["page"].fields["number"].required is True
    out = coerce_params({"filters": {"page": {"number": "2", "size": 20}}}, specs)
    assert out == {"filters": {"page": {"number": 2, "size": 20}}}
    with pytest.raises(BadRequest, match=r"filters\.page\.number.*>= 1"):
        coerce_params({"filters": {"page": {"number": 0, "size": 1}}}, specs)
    with pytest.raises(BadRequest, match="unknown field"):
        coerce_params({"filters": {"nope": 1}}, specs)


def test_a_bad_pattern_is_the_route_authors_error_not_the_clients():
    with pytest.raises(Exception):
        Pattern("[")

        def ep(self, x: Annotated[str, Pattern("[")]): ...

        _specs(ep)


def test_constraints_do_not_apply_to_objects_or_lists():
    class Point(TypedDict):
        x: int

    def ep(
        self, p: Annotated[Point, Range(ge=1)], xs: Annotated[list[int], Range(ge=1)]
    ): ...

    assert _specs(ep) == {}, "a range on an object or a list is declined, not misread"
