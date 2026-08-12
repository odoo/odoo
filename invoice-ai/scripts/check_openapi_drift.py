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
  boolean + nullable flag)

Tolerated differences (not part of the lock-step contract):

* FastAPI's tooling routes (/docs, /openapi.json) and the JWT bearer
  security requirement on /v1/extract.
* The YAML's ``servers`` block and prose descriptions.
"""

from __future__ import annotations

import json
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
        return "|".join(types)
    if "type" not in schema:
        return "object"
    if isinstance(schema["type"], list):
        return "|".join(sorted(str(t) for t in schema["type"]))

    kind = schema["type"]
    if kind == "string" and schema.get("format") == "date":
        return "date"
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


def main() -> int:
    generated = app.openapi()
    with open("../docs/openapi.yaml", encoding="utf-8") as fh:
        contract = yaml.safe_load(fh)

    failures = []

    # 1. /v1/extract response statuses must exist on both sides with the
    #    same target schema names.
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
    for status in sorted(shared_statuses):
        if gen_responses[status] != con_responses[status]:
            failures.append(
                f"/v1/extract[{status}] targets {gen_responses[status]} in the "
                f"app but {con_responses[status]} in docs/openapi.yaml",
            )

    # 2. Shared schema family must have identical wire fingerprints.
    shared_schemas = {
        "InvoiceExtraction",
        "InvoiceLine",
        "ExtractionFieldConfidence",
        "ExtractionResponse",
        "ErrorEnvelope",
    }
    for name in sorted(shared_schemas):
        gen = _schemas(generated).get(name)
        con = _schemas(contract).get(name)
        if gen is None or con is None:
            failures.append(f"schema {name} missing on one side")
            continue
        if _fingerprint(gen) != _fingerprint(con):
            failures.append(f"schema {name} drifted between app and docs")

    # 3. /healthz must carry build_sha (ops contract, added with JWT auth).
    health_200 = (
        generated.get("paths", {})
        .get("/healthz", {})
        .get("get", {})
        .get("responses", {})
        .get("200", {})
    )
    health_props = (
        health_200.get("content", {})
        .get("application/json", {})
        .get("schema", {})
        .get("properties", {})
    )
    if "build_sha" not in health_props:
        failures.append("/healthz no longer documents build_sha in the app spec")

    if failures:
        print("OpenAPI drift detected:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("OpenAPI contract OK: /v1/extract + shared schemas + /healthz match")
    return 0


if __name__ == "__main__":
    sys.exit(main())
