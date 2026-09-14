import io
from unittest.mock import patch

from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTTextBox
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install", "web_report")
class TestModuleReferenceValues(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report_model = cls.env["report.web.report_irmodulereference"]
        cls.base_module = cls.env["ir.module.module"].search([("name", "=", "base")])

    def test_attribution_follows_the_record_not_the_external_id(self):
        partner_field = self.env["ir.model.fields"].search(
            [("model", "=", "res.partner.bank"), ("name", "=", "id")], limit=1
        )
        self.assertTrue(partner_field, "res.partner.bank must expose an id field")
        self.env["ir.model.data"].sudo().create(
            {
                "module": "base",
                "name": "field_res_partner_impostor__id",
                "model": "ir.model.fields",
                "res_id": partner_field.id,
            }
        )

        names = self.report_model._get_field_names_by_model(self.base_module)

        self.assertIn(
            "id",
            names["base"]["res.partner.bank"],
            "the field belongs to the model its record names",
        )
        self.assertNotIn(
            "id",
            names["base"].get("res.partner.impostor", ()),
            "no model may be conjured out of an external ID's spelling",
        )

    def test_every_reported_field_is_declared_by_that_module_on_that_model(self):
        modules = self.env["ir.module.module"].search(
            [("state", "=", "installed")], limit=12
        )
        values = self.report_model._get_report_values(modules.ids)
        names = self.report_model._get_field_names_by_model(modules)

        for module in modules:
            for entry in values["objects_by_module"][module.name]:
                declared = set(names[module.name].get(entry["model"], ()))
                reported = {field["name"] for field in entry["fields"]}
                self.assertLessEqual(
                    reported,
                    declared,
                    f"{module.name} reports fields it does not declare on "
                    f"{entry['model']}",
                )

    def test_objects_are_keyed_per_module(self):
        modules = self.env["ir.module.module"].search(
            [("name", "in", ("base", "web")), ("state", "=", "installed")]
        )
        if len(modules) < 2:
            self.skipTest("needs both base and web installed")

        values = self.report_model._get_report_values(modules.ids)
        by_module = values["objects_by_module"]

        self.assertEqual(set(by_module), {"base", "web"})
        for module in modules:
            declared = set(
                self.report_model._get_models_by_module(module)[module.name].mapped(
                    "model"
                )
            )
            listed = {entry["model"] for entry in by_module[module.name]}
            self.assertEqual(listed, declared)

    def test_a_model_with_no_declared_field_describes_nothing(self):
        self.assertEqual(
            self.report_model._get_field_descriptions("res.partner", []), []
        )

    def test_a_model_absent_from_the_registry_is_skipped(self):
        self.assertEqual(
            self.report_model._get_field_descriptions("no.such.model", ["name"]), []
        )

    def test_a_model_whose_fields_get_raises_does_not_abort_the_document(self):
        boom = NotImplementedError("mixin must implement _get_order_type()")
        real_fields_get = type(self.env["res.partner"]).fields_get

        def fields_get(self, allfields=None, attributes=None):
            if self._name == "res.partner":
                raise boom
            return real_fields_get(self, allfields, attributes)

        with patch.object(type(self.env["res.partner"]), "fields_get", fields_get):
            described = self.report_model._get_field_descriptions(
                "res.partner", ["name"]
            )
            values = self.report_model._get_report_values(self.base_module.ids)

        self.assertEqual(described, [])
        objects = values["objects_by_module"]["base"]
        partner = next(e for e in objects if e["model"] == "res.partner")
        self.assertEqual(partner["fields"], [])
        self.assertTrue(
            any(e["fields"] for e in objects),
            "the other models must still carry their fields",
        )

    def test_report_values_carry_the_conventional_keys(self):
        values = self.report_model._get_report_values(self.base_module.ids)
        self.assertEqual(values["doc_ids"], self.base_module.ids)
        self.assertEqual(values["doc_model"], "ir.module.module")
        self.assertEqual(values["docs"], self.base_module)


class PdfGeometryCase(TransactionCase):
    def _render_pdf(self, report_ref, res_ids):
        pdf, extension = (
            self.env["ir.actions.report"]
            .with_context(force_report_rendering=True)
            ._render_qweb_pdf(report_ref, res_ids)
        )
        self.assertEqual(extension, "pdf")
        return pdf

    def _text_boxes(self, pdf):
        parser = PDFParser(io.BytesIO(pdf))
        pages = list(PDFPage.create_pages(PDFDocument(parser)))
        manager = PDFResourceManager()
        device = PDFPageAggregator(manager, laparams=LAParams())
        interpreter = PDFPageInterpreter(manager, device)
        for page in pages:
            interpreter.process_page(page)
            width = float(page.mediabox[2])
            for obj in device.get_result():
                if isinstance(obj, LTTextBox):
                    yield width, obj, obj.get_text().strip()


@tagged("post_install", "-at_install", "web_report")
class TestIntrospectionReportGeometry(PdfGeometryCase):
    def test_model_overview_stays_inside_the_page(self):
        model = self.env["ir.model"].search([("model", "=", "res.partner")])
        pdf = self._render_pdf("web.report_ir_model_overview", model.ids)

        overflowing = [
            (round(obj.x1 - width, 1), text)
            for width, obj, text in self._text_boxes(pdf)
            if obj.x1 - width > 1
        ]
        self.assertFalse(
            overflowing[:5],
            f"{len(overflowing)} text box(es) render past the right page edge",
        )

    def test_model_overview_prints_every_column_it_declares(self):
        model = self.env["ir.model"].search([("model", "=", "res.partner")])
        pdf = self._render_pdf("web.report_ir_model_overview", model.ids)
        rendered = "\n".join(text for _width, _obj, text in self._text_boxes(pdf))

        for heading in ("Flags", "Details", "External ID", "Rights"):
            self.assertIn(
                heading, rendered, f"the {heading!r} column never reached the PDF"
            )

    def test_module_reference_stays_inside_the_page(self):
        module = self.env["ir.module.module"].search([("name", "=", "base")])
        pdf = self._render_pdf("web.ir_module_reference_print", module.ids)

        overflowing = [
            (round(obj.x1 - width, 1), text)
            for width, obj, text in self._text_boxes(pdf)
            if obj.x1 - width > 1
        ]
        self.assertFalse(
            overflowing[:5],
            f"{len(overflowing)} text box(es) render past the right page edge",
        )
