"""Schema tests for InvoiceExtraction (Structured Outputs contract).

Covers the three hard rules from the task brief:
* ``additionalProperties: false`` everywhere (pydantic v2 emits it for the
  root and nested models when ``extra='forbid'``).
* explicit ``required`` — vendor_name, invoice_date, currency, amount_total
  and lines are required; the rest are Optional only where a real vendor
  invoice genuinely omits the field (VAT, due date, subtotal, tax total).
* no recursion and no numeric/length constraints — there is no
  ``Field(ge=...)`` or ``min_length``/``max_length`` anywhere in the schema.
  Constraining the prompt is the model's job.
"""

import json

from odoo.addons.invoice_agent.models import invoice_extraction
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestInvoiceExtractionSchema(TransactionCase):
    def test_valid_payload_validates(self):
        extraction = invoice_extraction.InvoiceExtraction.model_validate(
            {
                "vendor_name": "Acme Supplies LLC",
                "vendor_vat": "US123456789",
                "invoice_date": "2026-07-01",
                "due_date": "2026-07-31",
                "currency": "USD",
                "subtotal": 1350.0,
                "tax_total": 0.0,
                "amount_total": 1350.0,
                "lines": [
                    {
                        "name": "Server hosting",
                        "quantity": 1,
                        "price_unit": 850.0,
                    },
                ],
            },
        )
        self.assertEqual(extraction.vendor_name, "Acme Supplies LLC")
        self.assertEqual(str(extraction.invoice_date), "2026-07-01")
        self.assertEqual(float(extraction.amount_total), 1350.0)
        self.assertEqual(len(extraction.lines), 1)

    def test_optional_fields_accept_nulls(self):
        extraction = invoice_extraction.InvoiceExtraction.model_validate(
            {
                "vendor_name": "Berlin Logistik GmbH",
                "invoice_date": "2026-05-20",
                "currency": "EUR",
                "amount_total": 175.0,
                "lines": [],
            },
        )
        self.assertIsNone(extraction.vendor_vat)
        self.assertIsNone(extraction.due_date)
        self.assertIsNone(extraction.subtotal)
        self.assertIsNone(extraction.tax_total)

    def test_extra_properties_forbidden(self):
        import pydantic

        with self.assertRaises(pydantic.ValidationError):
            invoice_extraction.InvoiceExtraction.model_validate(
                {
                    "vendor_name": "Acme",
                    "invoice_date": "2026-07-01",
                    "currency": "USD",
                    "amount_total": 100.0,
                    "lines": [],
                    "mystery_field": "x",
                },
            )

    def test_missing_required_field_rejected(self):
        import pydantic

        with self.assertRaises(pydantic.ValidationError):
            invoice_extraction.InvoiceExtraction.model_validate(
                {
                    "vendor_name": "Acme",
                    "invoice_date": "2026-07-01",
                    "currency": "USD",
                    "lines": [],
                },
            )

    def test_json_schema_has_additional_properties_false_and_no_constraints(self):
        schema = invoice_extraction.InvoiceExtraction.model_json_schema()
        self.assertIs(schema["additionalProperties"], False)
        self.assertIn("required", schema)
        for required in (
            "vendor_name",
            "invoice_date",
            "currency",
            "amount_total",
            "lines",
        ):
            self.assertIn(required, schema["required"])

        # Nested line object honours additionalProperties: false. pydantic 2.13
        # emits nested models as $defs + $ref; follow the ref to the definition.
        lines_ref = schema["properties"]["lines"]["items"]
        if "$ref" in lines_ref:
            ref_name = lines_ref["$ref"].split("/")[-1]
            self.assertIs(schema["$defs"][ref_name]["additionalProperties"], False)
        else:
            self.assertIs(lines_ref["additionalProperties"], False)

        # No numeric or length constraints anywhere in the schema.
        dumped = json.dumps(schema)
        self.assertNotIn("minimum", dumped)
        self.assertNotIn("maximum", dumped)
        self.assertNotIn("minLength", dumped)
        self.assertNotIn("maxLength", dumped)

    def test_schema_has_no_recursive_reference(self):
        schema = invoice_extraction.InvoiceExtraction.model_json_schema()
        # pydantic 2.13 uses $defs for nested models; the contract forbids
        # *recursive* structures (a model referencing itself), so assert no
        # definition contains a $ref back into the schema. InvoiceLine has no
        # sub-models, so $defs holds no $ref at all.
        defs_dumped = json.dumps(schema.get("$defs", {}))
        self.assertNotIn("$ref", defs_dumped)
        for prop in schema.get("properties", {}).values():
            ref = prop.get("$ref")
            if ref:
                self.assertNotIn(schema["title"], ref)
