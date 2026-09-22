"""The doors' OpenAPI document: valid, and the checked-in copy is current.

`/web/openapi.json` describes whatever the server has installed, so it is a
different document on every database. `rpc`'s own doors are not: they are
this module's routes, they move only when this module does, and a client
generator reads them from the copy beside this file.
"""

import json
import os
import re
from pathlib import Path

from jsonschema import Draft202012Validator

from odoo.http import prepare_openapi_document
from odoo.http.openapi import OPENAPI_VERSION, iter_map_routes
from odoo.tests import common

DOCUMENT = Path(__file__).parent.parent / "machine_doc_v1" / "openapi.json"
TEMPLATE_ARG = re.compile(r"{(\w+)}")
WRITE = "ODOO_WRITE_OPENAPI"
REGENERATE = (
    f"{WRITE}=1 odoo-bin -d <db> --test-enable --test-tags "
    "/rpc:TestOpenAPIContract.test_the_checked_in_document_is_current"
)


def rpc_routes(routing_map):
    for route in iter_map_routes(routing_map):
        module = getattr(route.handler, "__module__", "")
        if module.startswith("odoo.addons.rpc."):
            yield route


@common.tagged("post_install", "-at_install")
class TestOpenAPIContract(common.TransactionCase):
    maxDiff = None

    def document(self):
        return prepare_openapi_document(
            rpc_routes(self.env["ir.http"].routing_map()),
            title="Odoo RPC",
            version="19.0",
        )

    def test_the_document_is_openapi_3_1(self):
        document = self.document()
        self.assertEqual(document["openapi"], OPENAPI_VERSION)
        self.assertEqual(document["info"], {"title": "Odoo RPC", "version": "19.0"})
        self.assertTrue(document["paths"], "rpc describes no door")

    def test_every_schema_in_it_is_a_schema(self):
        # OpenAPI 3.1's schema objects are JSON Schema 2020-12, so the
        # validator checks them without the network the meta-document needs.
        document = self.document()
        checked = 0
        for path, item in document["paths"].items():
            for verb, operation in item.items():
                for schema in self._schemas_of(operation):
                    with self.subTest(path=path, verb=verb):
                        Draft202012Validator.check_schema(schema)
                    checked += 1
        self.assertTrue(checked, "no operation of rpc carries a schema")

    def test_every_operation_is_named_once_and_declares_its_path_parameters(self):
        document = self.document()
        operation_ids = []
        for path, item in document["paths"].items():
            expected = set(TEMPLATE_ARG.findall(path))
            for verb, operation in item.items():
                operation_ids.append(operation["operationId"])
                declared = {
                    parameter["name"]
                    for parameter in operation.get("parameters", ())
                    if parameter["in"] == "path"
                }
                self.assertEqual(
                    declared,
                    expected,
                    f"{verb.upper()} {path} declares {declared} of {expected}",
                )
        self.assertEqual(
            sorted(operation_ids),
            sorted(set(operation_ids)),
            "two operations share an operationId, which no generator accepts",
        )

    def test_every_security_scheme_it_names_is_defined(self):
        document = self.document()
        defined = set(document.get("components", {}).get("securitySchemes", {}))
        for path, item in document["paths"].items():
            for verb, operation in item.items():
                for requirement in operation.get("security", ()):
                    for name in requirement:
                        self.assertIn(
                            name,
                            defined,
                            f"{verb.upper()} {path} requires {name!r}, which the "
                            "document does not define",
                        )

    def test_the_checked_in_document_is_current(self):
        current = self.document()
        if os.environ.get(WRITE):
            DOCUMENT.parent.mkdir(parents=True, exist_ok=True)
            DOCUMENT.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        self.assertTrue(DOCUMENT.exists(), f"{DOCUMENT} is missing; {REGENERATE}")
        self.assertEqual(
            json.loads(DOCUMENT.read_text()),
            current,
            f"the doors moved and the checked-in contract did not; {REGENERATE}",
        )

    def _schemas_of(self, operation):
        for parameter in operation.get("parameters", ()):
            if "schema" in parameter:
                yield parameter["schema"]
        body = operation.get("requestBody", {})
        for content in body.get("content", {}).values():
            if "schema" in content:
                yield content["schema"]
        for response in operation.get("responses", {}).values():
            for content in response.get("content", {}).values():
                if "schema" in content:
                    yield content["schema"]
