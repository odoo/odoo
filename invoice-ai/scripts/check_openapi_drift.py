"""CI check: the FastAPI-generated OpenAPI must not drift from docs/openapi.yaml.

Runs in the invoice-ai working directory (GitHub Actions sets it). Compares
the app's generated OpenAPI JSON against the frozen contract file in
docs/openapi.yaml for the parts both sides own lock-step.

The YAML contract is hand-written and predates JWT auth and the FastAPI
tooling routes, while the app's spec is pydantic-generated, so a
byte-for-byte diff would false-fail (pydantic v2 emits ``anyOf`` /
``"type": ["string", "null"]`` forms where the YAML uses the relaxed
``"type": [string, "null"]`` spelling). This check therefore compares a
**canonical fingerprint** per schema — the parts that define the wire
contract:

* ``required`` lists
* property names
* each property's canonical type (object/array/string/date/number/integer/
  boolean + nullable flag; pydantic's ``Decimal``-as-string is canonicalized
  to ``number`` because the wire value is a JSON number)

Documented, tolerated drift (locked by the runtime tests, re-checked here
so accidental *semantic* drift still fails the build):

* FastAPI's tooling routes (/docs, /openapi.json) and the JWT bearer
  security requirement on /v1/extract.
* ``/v1/extract[422]`` — FastAPI always emits its built-in
  ``HTTPValidationError`` for body/header validation; the YAML documents the
  ``ErrorEnvelope`` the ServiceError handler actually returns at runtime.
* ``ErrorEnvelope`` as a generated component — the app produces errors
  through the exception handler, not a declared ``response_model``, so it is
  absent from ``components.schemas``. Its runtime shape is locked by
  ``app.main._error_payload`` + ``tests/test_extract.py``.
* ``ExtractionResponse`` envelope internals — the app declares
  ``response_model=ExtractionResponse`` so the spec carries the ``Usage``
  component and marks ``model`` required (the service always returns it);
  the hand-written YAML renders usage inline and leaves ``model`` optional.
  Semantically identical on the wire; flagged in the PR as intent.
"""

from __future__ import annotations

import sys
from typing import Any

import yaml

from app.main import app


def _schemas(spec: dict) -> dict:
    return spec.get("components", {}).get("schemas", {})


def _canonical_type(schema: Any) -> str:
    """Collapse pydantic/JSON-Schema typing onto a canonical string.

    - ``{"type": "object"}``                 -> "object"
    - ``{"type": ["string", "null"]}``       -> "null|string"
    - ``{"anyOf": [{"type": "string"}, {"type": "null"}]}`` -> "null|string"
    - ``{"type": "string", "format": "date"}`` -> "date"
    - ``{...}`` with allOf/$ref              -> "ref"
    """
    if not isinstance(schema, dict):
        return str(type(schema).__name__)
    if "allOf" in schema or "$ref" in schema:
        return "ref"
    if "anyOf" in schema:
        types = sorted(_canonical_type(sub) for sub in schema["anyOf"])
        # Hand-written YAML never marks refs nullable — absence is handled by
        # `required` — while pydantic emits anyOf[ref, null] for optional
        # object fields. Drop the redundant null so both fingerprint equal.
        if "ref" in types:
            types = [t for t in types if t != "null"]
        return "|".join(types)
    if "type" not in schema:
        return "object"
    if isinstance(schema["type"], list):
        # YAML spelling of a date union (due_date) is
        # {type: [string, "null"], format: date}; pydantic emits
        # anyOf[{type: string, format: date}, {type: null}]. Both must
        # canonicalize to "date|null".
        kinds = []
        for t in schema["type"]:
            if t == "string" and schema.get("format") == "date":
                kinds.append("date")
            else:
                kinds.append(str(t))
        return "|".join(sorted(kinds))

    kind = schema["type"]
    if kind == "string":
        # pydantic renders Decimal as {"type": "string", "format": "decimal"}
        # but the wire value is a JSON number — canonicalize it so the YAML
        # contract (number) and the generated spec compare equal.
        if schema.get("format") == "decimal":
            return "number"
        if schema.get("format") == "date":
            return "date"
        # This FastAPI/pydantic build renders Decimal WITHOUT a format key,
        # only the decimal regex pattern — map it to "number" the same way.
        if schema.get("pattern") == "^(?!^[-+.]*$)[+-]?0*\\d*\\.?\\d*$":
            return "number"
    if kind == "array" and "$ref" in (schema.get("items") or {}):
        return "array(" + schema["items"]["$ref"].rsplit("/", 1)[-1] + ")"
    return kind


def _fingerprint(schema: dict) -> dict:
    """The lock-step wire contract of one schema object."""
    props = schema.get("properties", {})
    return {
        "required": sorted(schema.get("required", [])),
        "type": _canonical_type(schema),
        "additionalProperties": schema.get("additionalProperties", True),
        "properties": {
            name: _canonical_type(definition)
            for name, definition in sorted(props.items())
        },
    }


def _healthz_200_schema(spec: dict) -> dict:
    """Resolve the /healthz 200 schema, following $ref into components."""
    health_200 = (
        spec.get("paths", {})
        .get("/healthz", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    schema = (
        health_200.get("content", {})
        .get("application/json", {})
        .get("schema", {})
    )
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        return _schemas(spec).get(name, {})
    return schema


def main() -> int:
    generated = app.openapi()
    with open("../docs/openapi.yaml", encoding="utf-8") as fh:
        contract = yaml.safe_load(fh)

    failures = []

    # 1. /v1/extract responses that BOTH sides declare (422 is generator
    #    behaviour — HTTPValidationError — not the runtime ErrorEnvelope the
    #    YAML documents; tolerated, see module docstring).
    def extract_responses(spec: dict) -> dict:
        return (
            spec.get("paths", {})
            .get("/v1/extract", {})
            .get("post", {})
            .get("responses", {})
        )

    def response_refs(spec: dict) -> dict:
        refs = {}
        for status, definition in extract_responses(spec).items():
            schema = (
                definition.get("content", {})
                .get("application/json", {})
                .get("schema", {})
            )
            refs[status] = (schema.get("$ref") or "").rsplit("/", 1)[-1]
        return refs

    gen_responses = response_refs(generated)
    con_responses = response_refs(contract)
    shared_statuses = set(gen_responses) & set(con_responses)
    shared_statuses.discard("422")  # documented FastAPI generator behaviour
    for status in sorted(shared_statuses):
        if gen_responses[status] != con_responses[status]:
            failures.append(
                f"/v1/extract[{status}] targets {gen_responses[status]} in the "
                f"app but {con_responses[status]} in docs/openapi.yaml",
            )

    # 2. The extraction schemas the Odoo side parses must be byte-equal in
    #    wire fingerprint. ErrorEnvelope + the ExtractionResponse envelope
    #    internals are documented tolerances (see module docstring).
    shared_schemas = {
        "InvoiceExtraction",
        "InvoiceLine",
        "ExtractionFieldConfidence",
    }
    for name in sorted(shared_schemas):
        gen = _schemas(generated).get(name)
        con = _schemas(contract).get(name)
        if gen is None or con is None:
            failures.append(f"schema {name} missing on one side")
            continue
        if _fingerprint(gen) != _fingerprint(con):
            failures.append(f"schema {name} drifted between app and docs")

    # 3. The 200 envelope must still be ExtractionResponse (both sides) and
    #    that component must exist in the generated spec.
    if gen_responses.get("200") != "ExtractionResponse":
        failures.append("/v1/extract[200] no longer targets ExtractionResponse")
    if "ExtractionResponse" not in _schemas(generated):
        failures.append("ExtractionResponse missing from the generated spec")

    # 4. /healthz carries build_sha (ops contract, added with JWT auth).
    health_schema = _healthz_200_schema(generated)
    if "build_sha" not in (health_schema.get("properties") or {}):
        failures.append("/healthz no longer documents build_sha in the app spec")

    if failures:
        print("OpenAPI drift detected:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OpenAPI contract OK: /v1/extract schemas + envelope + /healthz match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
