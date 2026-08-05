"""Schema tests for InvoiceExtraction (Structured Outputs contract).

Covers the three hard rules from the task brief:
* ``additionalProperties: false`` everywhere (pydantic v2 emits it for the
  root and nested models when ``extra='forbid'``).
* explicit ``required`` — vendor_name, invoice_date, currency, amount_total
  and lines are required; the rest are Optional only where a real vendor
  invoice genuinely omits the field (VAT, due date, subtotal, tax total).
* no numeric/length constraints — there is no ``Field(ge=...)`` or
  ``min_length``/``max_length`` anywhere in the schema definition.

Skipped when pydantic is absent (stale image), so the suite stays runnable
before the image rebuild.
"""

import json

from odoo.tests import TransactionCase, skipIf, tagged

try:
    import pydantic

    PYDANTIC_AVAILABLE = True
except ImportError:
    pydantic = None
    PYDANTIC_AVAILABLE = False

from odoo.addons.invoice_agent.models import invoice_extraction


@tagged("post_install", "-at_install")
class TestInvoiceExtractionSchema(TransactionCase):

    @skipIf(not PYDANTIC_AVAILABLE, "pydantic not installed on this image")
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

    @skipIf(not PYDANTIC_AVAILABLE, "pydantic not installed on this image")
    def test_optional_fields_accept_nulls(self):
        # vendor_vat / due_date / subtotal / tax_total may be omitted.
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

    @skipIf(not PYDANTIC_AVAILABLE, "pydantic not installed on this image")
    def test_extra_properties_forbidden(self):
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

    @skipIf(not PYDANTIC_AVAILABLE, "pydantic not installed on this image")
    def test_missing_required_field_rejected(self):
        with self.assertRaises(pydantic.ValidationError):
            invoice_extraction.InvoiceExtraction.model_validate(
                {
                    "vendor_name": "Acme",
                    "invoice_date": "2026-07-01",
                    "currency": "USD",
                    # amount_total missing
                    "lines": [],
                },
            )

    @skipIf(not PYDANTIC_AVAILABLE, "pydantic not installed on this image")
    def test_json_schema_has_additional_properties_false_and_no_constraints(self):
        schema = invoice_extraction.InvoiceExtraction.model_json_schema()
        self.assertIs(schema["additionalProperties"], False)
        self.assertIn("required", schema)
        for required in ("vendor_name", "invoice_date", "currency", "amount_total", "lines"):
            self.assertIn(required, schema["required"])

        # Nested line object honours additionalProperties: false too.
        lines_schema = schema["properties"]["lines"]
        self.assertEqual(lines_schema["items"]["additionalProperties"], False)

        # No numeric or length constraints anywhere in the schema.
        dumped = json.dumps(schema)
        self.assertNotIn("minimum", dumped)
        self.assertNotIn("maximum", dumped)
        self.assertNotIn("minLength", dumped)
        self.assertNotIn("maxLength", dumped)

    @skipIf(not PYDANTIC_AVAILABLE, "pydantic not installed on this image")
    def test_schema_has_no_recursive_reference(self):
        schema = invoice_extraction.InvoiceExtraction.model_json_schema()
        dumped = json.dumps(schema)
        self.assertNotIn("$ref", dumped)
        self.assertNotIn("definitions", dumped)
