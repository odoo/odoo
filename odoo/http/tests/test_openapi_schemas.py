import dataclasses

from odoo.http.openapi import RouteInfo, get_response_schema, prepare_openapi_document


@dataclasses.dataclass
class Point:
    x: int
    y: int = 0


@dataclasses.dataclass
class Payload:
    name: str
    points: list[Point]
    origin: Point | None = None


def _route(rule, handler, **routing):
    return RouteInfo(
        rule=rule,
        methods=frozenset({"POST"}),
        routing={"type": "json2", "auth": "none", "typed": True, **routing},
        handler=handler,
    )


def test_a_dataclass_parameter_documents_an_object_schema():
    def ep(self, p: Payload): ...

    doc = prepare_openapi_document([_route("/shape", ep)])
    body = doc["paths"]["/shape"]["post"]["requestBody"]["content"]["application/json"]
    payload = body["schema"]["properties"]["p"]
    assert payload["type"] == "object"
    assert payload["required"] == ["name", "points"]
    assert payload["additionalProperties"] is False
    assert payload["properties"]["points"] == {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
            "additionalProperties": False,
            "required": ["x"],
        },
    }
    assert payload["properties"]["origin"]["type"] == ["object", "null"]


def test_a_return_annotation_documents_the_response_for_json_routes():
    def ep(self, p: Point) -> Point:
        raise NotImplementedError

    doc = prepare_openapi_document([_route("/echo", ep)])
    ok = doc["paths"]["/echo"]["post"]["responses"]["200"]
    assert ok["content"]["application/json"]["schema"]["type"] == "object"

    rpc = prepare_openapi_document([_route("/rpc", ep, type="jsonrpc")])
    envelope = rpc["paths"]["/rpc"]["post"]["responses"]["200"]["content"]
    result = envelope["application/json"]["schema"]["properties"]["result"]
    assert result["type"] == "object"


def test_http_routes_and_unannotated_returns_document_no_body():
    def ep(self, p: Point): ...

    doc = prepare_openapi_document([_route("/h", ep, type="http")])
    assert "content" not in doc["paths"]["/h"]["post"]["responses"]["200"]
    assert get_response_schema(ep) is None


def test_dict_and_list_returns_are_described():
    def as_dict(self) -> dict[str, int]:
        raise NotImplementedError

    def as_list(self) -> list[Point]:
        raise NotImplementedError

    assert get_response_schema(as_dict) == {"type": "object"}
    as_list_schema = get_response_schema(as_list)
    assert as_list_schema is not None
    assert as_list_schema["type"] == "array"
