import typing

import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest

from odoo.http._params import (
    ParamSpec,
    coerce_params,
    get_param_specs,
)


def _spec(fn):
    return get_param_specs(fn)


def test_the_three_optional_spellings_build_one_spec():
    optional = typing.Optional  # noqa: TID251  legacy spelling under test
    union = typing.Union  # noqa: TID251  legacy spelling under test

    def ep(
        self,
        a: int | None,
        b: optional[int],  # type: ignore[valid-type]
        c: union[int, None],  # type: ignore[valid-type]
        d: int | str,
    ): ...

    specs = _spec(ep)
    assert specs["a"] == specs["b"] == specs["c"] == ParamSpec(int, None, True, True)
    assert "d" not in specs, "a two-type union is not coerced"


def test_list_forms():
    legacy_list = list

    def ep(
        self,
        a: list,
        b: list[int],
        c: legacy_list[int],  # type: ignore[valid-type]
        d: list[dict],
    ): ...

    specs = _spec(ep)
    assert (specs["a"].target, specs["a"].item) == (list, None)
    assert (specs["b"].target, specs["b"].item) == (list, int)
    assert (specs["c"].target, specs["c"].item) == (list, int)
    assert (specs["d"].target, specs["d"].item) == (list, None)


def test_build_specs_skips_unannotated_and_unsupported():
    def ep(self, n: int, raw, note: bytes = b"", opt: int | None = None): ...

    specs = _spec(ep)
    assert set(specs) == {"n", "opt"}
    assert specs["n"] == ParamSpec(int, None, False, True)
    assert specs["opt"] == ParamSpec(int, None, True, False)


def test_scalar_coercions():
    def ep(self, n: int, x: float, flag: bool, name: str): ...

    out = coerce_params({"n": "5", "x": "2.5", "flag": "on", "name": 7}, _spec(ep))
    assert out == {"n": 5, "x": 2.5, "flag": True, "name": "7"}


@pytest.mark.parametrize("bad", ["abc", "3.7", "0x10", "", "1e999"])
def test_int_rejects_non_integers(bad):
    def ep(self, n: int): ...

    with pytest.raises(BadRequest):
        coerce_params({"n": bad}, _spec(ep))


def test_int_rejects_bool_and_fractional_float():
    def ep(self, n: int): ...

    for bad in (True, 3.7):
        with pytest.raises(BadRequest):
            coerce_params({"n": bad}, _spec(ep))
    assert coerce_params({"n": 3.0}, _spec(ep)) == {"n": 3}


def test_float_rejects_non_finite():
    def ep(self, x: float): ...

    for bad in ("nan", "inf", "-inf"):
        with pytest.raises(BadRequest):
            coerce_params({"x": bad}, _spec(ep))


@pytest.mark.parametrize("bad", ["1_000", "١٢", "٥", "1 "])
def test_int_rejects_python_only_number_spellings(bad):

    def ep(self, n: int): ...

    with pytest.raises(BadRequest):
        coerce_params({"n": bad}, _spec(ep))


@pytest.mark.parametrize("bad", ["1_000.5", "٥.٥", "1_0e3"])
def test_float_rejects_python_only_number_spellings(bad):
    def ep(self, x: float): ...

    with pytest.raises(BadRequest):
        coerce_params({"x": bad}, _spec(ep))


def test_number_coercion_still_tolerates_surrounding_whitespace():

    def ep(self, n: int, x: float): ...

    assert coerce_params({"n": "  42 ", "x": " 3.14 "}, _spec(ep)) == {
        "n": 42,
        "x": 3.14,
    }


@pytest.mark.parametrize(
    "value",
    [
        FileStorage(filename="a.png"),
        b"raw-bytes",
        {"a": 1},
        [1, 2],
    ],
)
def test_str_param_rejects_non_scalars(value):

    def ep(self, note: str): ...

    with pytest.raises(BadRequest):
        coerce_params({"note": value}, _spec(ep))


def test_str_param_stringifies_json_numbers():
    def ep(self, note: str): ...

    assert coerce_params({"note": 5}, _spec(ep)) == {"note": "5"}
    assert coerce_params({"note": 2.5}, _spec(ep)) == {"note": "2.5"}


def test_str_param_rejects_bool():

    def ep(self, note: str): ...

    with pytest.raises(BadRequest):
        coerce_params({"note": True}, _spec(ep))


def test_string_annotations_are_resolved():

    def ep(self, n: "int", opt: "int | None" = None): ...  # noqa: UP037  the string form is what is under test

    specs = _spec(ep)
    assert specs["n"] == ParamSpec(int, None, False, True)
    assert specs["opt"] == ParamSpec(int, None, True, False)
    assert coerce_params({"n": "5"}, specs) == {"n": 5}


def test_unresolvable_string_annotation_passes_through():

    def ep(self, n: "int", ghost: "NotARealName" = None): ...  # type: ignore[name-defined]  # noqa: UP037, F821  an unresolvable annotation is the case

    specs = _spec(ep)
    assert set(specs) == {"n"}
    assert specs["n"] == ParamSpec(int, None, False, True)


def test_required_missing_raises_optional_missing_skips():
    def ep(self, n: int, opt: int | None = None): ...

    specs = _spec(ep)
    with pytest.raises(BadRequest):
        coerce_params({}, specs)
    assert coerce_params({"n": 1}, specs) == {"n": 1}


def test_null_only_allowed_when_optional():
    def ep(self, n: int, opt: int | None = None): ...

    with pytest.raises(BadRequest):
        coerce_params({"n": None}, _spec(ep))
    assert coerce_params({"n": 1, "opt": None}, _spec(ep)) == {"n": 1, "opt": None}


def test_list_of_ints_and_untyped_list():
    def ep(self, ids: list[int] | None = None, raw: list | None = None): ...

    specs = _spec(ep)
    assert coerce_params({"ids": ["1", "2"], "raw": ["a", 3]}, specs) == {
        "ids": [1, 2],
        "raw": ["a", 3],
    }
    assert coerce_params({"ids": "7"}, specs) == {"ids": [7]}


_FUZZ_TARGETS = [
    (int, None),
    (float, None),
    (bool, None),
    (str, None),
    (list, None),
    (list, int),
    (list, float),
    (list, bool),
    (list, str),
]

_FUZZ_VALUES = [
    None,
    True,
    False,
    0,
    1,
    -1,
    2**63,
    10**500,
    0.0,
    1.5,
    float("nan"),
    float("inf"),
    float("-inf"),
    1e308,
    "",
    " ",
    "0",
    "  12  ",
    "+12",
    "1_000",
    "0x10",
    "1e3",
    "true",
    "  yes ",
    "maybe",
    "nan",
    "inf",
    "١٢٣",
    "１２３",
    "9" * 5000,
    "\x00",
    [],
    [1, 2],
    [None],
    [[1]],
    [{"a": 1}],
    (1, 2),
    {"a": 1},
    {},
    b"12",
    bytearray(b"1"),
    range(3),
    object(),
]


@pytest.mark.parametrize(("target", "item"), _FUZZ_TARGETS)
@pytest.mark.parametrize("allow_none", [True, False])
def test_no_value_escapes_coercion_as_anything_but_a_bad_request(
    target, item, allow_none
):
    spec = {
        "p": ParamSpec(target=target, item=item, allow_none=allow_none, required=True)
    }
    for value in _FUZZ_VALUES:
        try:
            coerce_params({"p": value}, spec)
        except BadRequest:
            pass
        except Exception as exc:
            pytest.fail(
                f"target={target.__name__} item={item} allow_none={allow_none} "
                f"value={value!r} escaped as {type(exc).__name__}: {exc}"
            )


def test_an_int_too_large_for_a_double_is_a_bad_request_not_a_crash():
    spec = {"n": ParamSpec(target=float, item=None, allow_none=False, required=True)}
    with pytest.raises(BadRequest, match="must be a finite number"):
        coerce_params({"n": int("9" * 400)}, spec)


def test_the_int_converter_werkzeug_hands_us_really_is_unbounded():
    import werkzeug.routing

    adapter = werkzeug.routing.Map(
        [werkzeug.routing.Rule("/r/<int:n>", endpoint="e")]
    ).bind("h")
    _, args = adapter.match("/r/" + "9" * 400, return_rule=True)

    assert isinstance(args["n"], int)
    assert args["n"].bit_length() > 1024
