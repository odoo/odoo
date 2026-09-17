import dataclasses
from typing import Annotated, Literal, TypedDict

import pytest
from werkzeug.exceptions import BadRequest

from odoo.http._params import Discriminator, coerce_params, get_param_specs
from odoo.http.openapi import RouteInfo, prepare_openapi_document


@dataclasses.dataclass
class Card:
    kind: Literal["card"]
    number: str
    cvc: int


class Wire(TypedDict):
    kind: Literal["wire"]
    iban: str


Payment = Annotated[Card | Wire, Discriminator("kind")]


def _specs(fn):
    return get_param_specs(fn)


def test_the_tag_picks_the_variant_and_the_variant_validates_the_rest():
    def ep(self, payment: Payment): ...

    specs = _specs(ep)
    assert set(specs["payment"].variants) == {"card", "wire"}
    out = coerce_params(
        {"payment": {"kind": "card", "number": "4242", "cvc": "123"}}, specs
    )
    assert out == {"payment": Card("card", "4242", 123)}
    out = coerce_params({"payment": {"kind": "wire", "iban": "DE00"}}, specs)
    assert out == {"payment": {"kind": "wire", "iban": "DE00"}}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("card", "must be an object"),
        ({"number": "4242"}, "must carry 'kind'"),
        ({"kind": "cash"}, "'kind' must be one of"),
        ({"kind": "card", "number": "4242"}, "missing required field 'cvc'"),
        ({"kind": "wire", "iban": "DE00", "cvc": 1}, "unknown field"),
    ],
)
def test_a_malformed_union_value_is_a_400_naming_the_problem(value, message):
    def ep(self, payment: Payment): ...

    with pytest.raises(BadRequest, match=message):
        coerce_params({"payment": value}, _specs(ep))


def test_an_optional_union_accepts_null():
    def ep(self, payment: Payment | None = None): ...

    specs = _specs(ep)
    assert specs["payment"].allow_none and not specs["payment"].required
    assert coerce_params({"payment": None}, specs) == {"payment": None}


def test_a_union_without_a_unique_tag_per_member_is_declined():
    @dataclasses.dataclass
    class Untagged:
        number: str

    @dataclasses.dataclass
    class Both:
        kind: Literal["card", "wire"]

    def no_tag(self, p: Annotated[Card | Untagged, Discriminator("kind")]): ...

    def two_tags(self, p: Annotated[Card | Both, Discriminator("kind")]): ...

    def no_marker(self, p: Card | Wire): ...

    assert _specs(no_tag) == {}
    assert _specs(two_tags) == {}
    assert _specs(no_marker) == {}, "an undiscriminated union stays uncoerced"


def test_an_object_param_on_an_http_route_is_omitted_with_a_warning(caplog):
    def ep(self, payment: Payment, page: int = 1): ...

    route = RouteInfo(
        rule="/pay",
        methods=frozenset({"GET"}),
        routing={"type": "http", "auth": "none", "typed": True},
        handler=ep,
    )
    with caplog.at_level("WARNING", logger="odoo.http.openapi"):
        doc = prepare_openapi_document([route])
    params = doc["paths"]["/pay"]["get"].get("parameters", [])
    names = {p["name"] for p in params}
    assert "payment" not in names, "the http dispatcher can never deliver a dict"
    assert "page" in names, "scalar query parameters stay documented"
    assert any("payment" in r.message for r in caplog.records)


def test_a_nullable_union_gains_a_null_variant_not_the_removed_nullable_keyword():
    def ep(self, payment: Payment | None = None): ...

    route = RouteInfo(
        rule="/pay",
        methods=frozenset({"POST"}),
        routing={"type": "json2", "auth": "none", "typed": True},
        handler=ep,
    )
    doc = prepare_openapi_document([route])
    body = doc["paths"]["/pay"]["post"]["requestBody"]["content"]["application/json"]
    schema = body["schema"]["properties"]["payment"]
    assert "nullable" not in schema, "OpenAPI 3.1 removed the 3.0 keyword"
    assert schema["oneOf"][-1] == {"type": "null"}
    assert schema["discriminator"] == {"propertyName": "kind"}


def test_the_union_is_documented_as_one_of_with_its_discriminator():
    def ep(self, payment: Payment): ...

    route = RouteInfo(
        rule="/pay",
        methods=frozenset({"POST"}),
        routing={"type": "json2", "auth": "none", "typed": True},
        handler=ep,
    )
    doc = prepare_openapi_document([route])
    body = doc["paths"]["/pay"]["post"]["requestBody"]["content"]["application/json"]
    schema = body["schema"]["properties"]["payment"]
    assert schema["discriminator"] == {"propertyName": "kind"}
    kinds = [v["properties"]["kind"]["enum"] for v in schema["oneOf"]]
    assert kinds == [["card"], ["wire"]]
