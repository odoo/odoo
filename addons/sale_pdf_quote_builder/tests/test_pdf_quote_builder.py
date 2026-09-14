import json
from base64 import b64encode
from functools import partial
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.http import Response
from odoo.tests import Form, tagged
from odoo.tools.misc import file_open

from .files import forms_pdf, plain_pdf
from odoo.addons.sale.tests.common import SaleOrderTemplateCommon
from odoo.addons.sale_pdf_quote_builder.controllers.quotation_document import (
    QuotationDocumentController,
)


@tagged("-at_install", "post_install")
class TestPDFQuoteBuilder(SaleOrderTemplateCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.QuotationDocumentController = QuotationDocumentController()

        cls.sale_order.date_validity = "2020-11-04"
        cls.sale_order.partner_id.tz = "Europe/Brussels"
        cls.env["document.document"].search([("type", "!=", "folder")]).action_archive()
        cls.env["quotation.document"].search([]).action_archive()

        with file_open(forms_pdf, "rb") as file:
            forms_pdf_data = b64encode(file.read())

        with file_open(plain_pdf, "rb") as file:
            plain_pdf_data = b64encode(file.read())

        att_header, att_footer, att_prod_doc = cls.env["ir.attachment"].create(
            [
                {
                    "name": "Header",
                    "datas": plain_pdf_data,
                },
                {
                    "name": "Footer",
                    "datas": forms_pdf_data,
                },
                {
                    "name": "Product Document",
                    "datas": forms_pdf_data,
                },
            ]
        )
        cls.header, cls.footer = cls.env["quotation.document"].create(
            [
                {
                    "name": "Header",
                    "ir_attachment_id": att_header.id,
                    "document_type": "header",
                },
                {
                    "name": "Footer",
                    "ir_attachment_id": att_footer.id,
                    "document_type": "footer",
                },
            ]
        )
        cls.product_document = cls.env["document.document"].create(
            {
                "name": "Product Document",
                "attachment_id": att_prod_doc.id,
                "attached_on_sale": "inside",
                "res_model": "product.product",
                "res_id": cls.product.id,
            }
        )
        cls.internal_user = cls._create_new_internal_user(
            login="internal.user@test.odoo.com", groups="sale.group_sale_salesman"
        )
        cls.alt_company = cls.env["res.company"].create({"name": "Backup Company"})

    def _create_so_form(self, **values):
        SaleOrder = self.env["sale.order"].with_context(
            default_partner_id=self.partner.id
        )
        so_form = Form(SaleOrder)
        for field_name, value in values.items():
            so_form[field_name] = value
        so_form.save()
        return so_form

    @staticmethod
    def _copy_on_same_record(document):
        return document.copy(
            {"res_model": document.res_model, "res_id": document.res_id}
        )

    def test_compute_customizable_pdf_form_fields_when_no_file(self):
        self.env["quotation.document"].search([]).action_archive()
        self.env["document.document"].search(
            [("type", "!=", "folder")]
        ).action_archive()
        self.assertEqual(self.sale_order.customizable_pdf_form_fields, False)

    def test_dynamic_fields_mapping_for_quotation_document(self):
        FormField = self.env["sale.pdf.form.field"]
        new_form_field = partial(dict, document_type="quotation_document")
        new_form_fields = FormField.create(
            [
                new_form_field(name="boolean_test", path="locked"),
                new_form_field(name="char_test", path="name"),
                new_form_field(name="date_test", path="date_validity"),
                new_form_field(name="datetime_test", path="date_commitment"),
                new_form_field(name="float_test", path="prepayment_percent"),
                new_form_field(name="integer_test", path="company_id.color"),
                new_form_field(name="selection_test", path="state"),
                new_form_field(name="monetary_test", path="amount_total"),
                new_form_field(name="one2many_test", path="line_ids"),
                new_form_field(name="many2one_test", path="company_id"),
                new_form_field(name="many2many_test", path="company_id.parent_ids"),
            ]
        )
        sol_1, sol_2 = self.sale_order.line_ids
        form_field_expected_value_map = {
            new_form_fields[0]: "No",
            new_form_fields[1]: self.sale_order.name,
            new_form_fields[2]: "11/04/2020",
            new_form_fields[3]: "",
            new_form_fields[4]: "1.0",
            new_form_fields[5]: "1",
            new_form_fields[6]: dict(self.sale_order._fields["state"].selection)[
                "draft"
            ],
            new_form_fields[7]: "$\xa0725.00",
            new_form_fields[8]: f"{sol_1.display_name}, {sol_2.display_name}",
            new_form_fields[9]: f"{self.sale_order.company_id.display_name}",
            new_form_fields[10]: f"{self.sale_order.company_id.display_name}",
        }
        for form_field, expected_value in form_field_expected_value_map.items():
            result = self.env["ir.actions.report"]._get_value_from_path(
                form_field, self.sale_order
            )
            self.assertEqual(result, expected_value)

    def test_dynamic_fields_mapping_for_product_document(self):
        self.sale_order.date_commitment = "2121-12-21 12:21:12"
        sol_1, sol_2 = self.sale_order.line_ids
        sol_1.update(
            {
                "sequence": 0,
                "discount": 4.99,
                "tax_ids": [
                    Command.create({"name": "test tax1"}),
                    Command.create({"name": "test tax2"}),
                ],
            }
        )
        new_form_field = partial(dict, document_type="product_document")
        new_form_fields = self.env["sale.pdf.form.field"].create(
            [
                new_form_field(name="boolean_test", path="order_id.locked"),
                new_form_field(name="char_test", path="order_id.name"),
                new_form_field(name="date_test", path="order_id.date_validity"),
                new_form_field(name="datetime_test", path="order_id.date_commitment"),
                new_form_field(name="float_test", path="discount"),
                new_form_field(name="integer_test", path="sequence"),
                new_form_field(name="selection_test", path="order_id.state"),
                new_form_field(name="monetary_test", path="order_id.amount_total"),
                new_form_field(name="one2many_test", path="order_id.line_ids"),
                new_form_field(name="many2one_test", path="order_id.company_id"),
                new_form_field(name="many2many_test", path="tax_ids"),
            ]
        )
        expected = {
            "boolean_test": "No",
            "char_test": self.sale_order.name,
            "date_test": "11/04/2020",
            "datetime_test": "12/21/2121 01:21:12 PM",
            "float_test": "4.99",
            "integer_test": "0",
            "selection_test": dict(self.sale_order._fields["state"].selection)["draft"],
            "monetary_test": self.sale_order.currency_id.format(720.01),
            "one2many_test": f"{sol_1.display_name}, {sol_2.display_name}",
            "many2one_test": self.sale_order.company_id.display_name,
            "many2many_test": "test tax1, test tax2",
        }
        for form_field in new_form_fields:
            result = self.env["ir.actions.report"]._get_value_from_path(
                form_field, self.sale_order, sol_1
            )
            self.assertEqual(
                " ".join(result.split()), " ".join(expected[form_field.name].split())
            )

    def test_product_document_dialog_params_access(self):
        sale_order_internal_user = self.sale_order.copy(
            {"user_id": self.internal_user.id}
        )
        dialog_param = sale_order_internal_user.with_user(
            self.internal_user.id
        ).get_update_included_pdf_params()
        self.assertEqual("Header", dialog_param["headers"]["files"][0]["name"])
        self.assertEqual("Product > Test Product", dialog_param["lines"][0]["name"])

    def test_quotation_document_is_removed_on_template_change(self):
        so_tmpl = self.env["sale.order.template"].create(
            {
                "name": "test1",
                "quotation_document_ids": [Command.link(self.header.id)],
            }
        )
        so_tmpl_2 = self.env["sale.order.template"].create({"name": "test2"})

        self.sale_order.write(
            {
                "sale_order_template_id": so_tmpl.id,
                "quotation_document_ids": [Command.link(self.header.id)],
            }
        )

        self.assertEqual(self.sale_order.quotation_document_ids, self.header)

        so_form = Form(self.sale_order)
        so_form.sale_order_template_id = so_tmpl_2
        so_form.save()

        self.assertNotIn(self.header, self.sale_order.available_quotation_document_ids)
        self.assertEqual(len(self.sale_order.quotation_document_ids), 0)

    def test_non_pdf_attachment_inside_quote_form_save(self):
        non_pdf_att = self.env["ir.attachment"].create(
            {
                "name": "Not a PDF",
                "datas": b64encode(b"hello"),
                "mimetype": "text/plain",
            }
        )

        product_document = self.product_document

        product_document.write(
            {
                "attachment_id": non_pdf_att.id,
            }
        )
        with self.assertRaises(ValidationError):
            with Form(
                product_document,
                view="document_product.view_documents_document_product_form",
            ) as doc_form:
                doc_form.attached_on_sale = "inside"

    def test_onchange_product_removes_previously_selected_documents(self):

        available_doc = self.sale_order.line_ids[0].available_product_document_ids
        self.sale_order.line_ids[0].product_document_ids = available_doc

        self.assertTrue(
            available_doc, msg="Default order line should have an available document."
        )
        msg = "The available document should have been selected."
        self.assertEqual(
            self.sale_order.line_ids[0].product_document_ids, available_doc, msg=msg
        )

        so_form = Form(self.sale_order)
        with so_form.line_ids.edit(0) as line:
            line.product_id = self._create_product()
        so_form.save()

        msg = "There shouldn't be any available product documents."
        self.assertFalse(
            self.sale_order.line_ids[0].available_product_document_ids, msg=msg
        )
        msg = "There shouldn't be any selected product documents left."
        self.assertFalse(self.sale_order.line_ids[0].product_document_ids, msg=msg)

    def test_available_documents_order(self):
        product_document = self._copy_on_same_record(self.product_document)
        product_document.sequence = self.product_document.sequence - 1
        docs = self.sale_order.line_ids[0].available_product_document_ids
        self.assertEqual(len(docs), 2, "There should be 2 available documents.")
        self.assertEqual(
            docs[0],
            product_document,
            "The first available document should be the one with the lowest sequence.",
        )
        self.assertEqual(
            docs[1],
            self.product_document,
            "The second available document should be the one with the highest sequence.",
        )

    def test_available_documents_multiple_products(self):
        product_doc_copy = self._copy_on_same_record(self.product_document)
        product2 = self._create_product(name="Test Product 2")
        product_template_document2 = self.product_document.copy(
            {
                "res_model": "product.template",
                "res_id": product2.product_tmpl_id.id,
                "sequence": 1,
            }
        )
        product_document2 = self.product_document.copy(
            {"res_model": "product.product", "res_id": product2.id, "sequence": 99}
        )
        self.sale_order.write(
            {
                "line_ids": [
                    Command.create({"product_id": self.product.id}),
                    Command.create({"product_id": product2.id}),
                ]
            }
        )
        self.assertEqual(
            self.sale_order.line_ids[0].available_product_document_ids,
            self.product_document | product_doc_copy,
        )
        self.assertFalse(
            self.sale_order.line_ids[1].available_product_document_ids,
            "The second order line should not have any available product documents.",
        )
        self.assertEqual(
            self.sale_order.line_ids[0].available_product_document_ids,
            self.sale_order.line_ids[2].available_product_document_ids,
            "The first and third order lines should have the same available product documents.",
        )
        self.assertEqual(
            self.sale_order.line_ids[3].available_product_document_ids[0].res_model,
            "product.product",
            "Alphabetical order of res_model should be respected.",
        )
        self.assertEqual(
            self.sale_order.line_ids[3].available_product_document_ids[0],
            product_document2,
        )
        self.assertEqual(
            self.sale_order.line_ids[3].available_product_document_ids[1],
            product_template_document2,
        )

    def test_quotation_document_upload_no_template(self):
        if "website" not in self.env:
            self.skipTest("Module `website` not found")
        else:
            from odoo.addons.http_routing.tests.common import MockRequest

        with (
            MockRequest(self.env) as request,
            file_open(plain_pdf, "rb") as file,
            patch.object(
                request.httprequest.files, "getlist", lambda _key: [FileStorage(file)]
            ),
            patch.object(
                request,
                "prepare_json_response",
                lambda data, status=200, headers=None: Response(
                    json.dumps(data),
                    status=status,
                    headers=headers,
                    mimetype="application/json",
                ),
            ),
        ):
            res = self.QuotationDocumentController.upload_document(
                ufile=FileStorage(file),
                allowed_company_ids=json.dumps(
                    [self.alt_company.id, self.env.company.id]
                ),
            )
            self.assertEqual(res.status_code, 200, "Upload should be successful")

        quotation_document = self.env["quotation.document"].search(
            [
                ("name", "=", plain_pdf),
            ],
            limit=1,
        )
        self.assertTrue(
            quotation_document, "A new quotation document should be created"
        )
        self.assertEqual(
            quotation_document.company_id,
            self.alt_company,
            "Quotation document company should be the currently active company",
        )

    def test_quotation_document_upload_for_template(self):
        if "website" not in self.env:
            self.skipTest("Module `website` not found")
        else:
            from odoo.addons.http_routing.tests.common import MockRequest

        self.empty_order_template.company_id = False
        with (
            MockRequest(self.env) as request,
            file_open(forms_pdf, "rb") as file,
            patch.object(
                request.httprequest.files, "getlist", lambda _key: [FileStorage(file)]
            ),
            patch.object(
                request,
                "prepare_json_response",
                lambda data, status=200, headers=None: Response(
                    json.dumps(data),
                    status=status,
                    headers=headers,
                    mimetype="application/json",
                ),
            ),
        ):
            res = self.QuotationDocumentController.upload_document(
                ufile=FileStorage(file),
                sale_order_template_id=str(self.empty_order_template.id),
                allowed_company_ids=json.dumps(
                    [self.alt_company.id, self.env.company.id]
                ),
            )
            self.assertEqual(res.status_code, 200, "Upload should be successful")

        quotation_document = self.env["quotation.document"].search(
            [
                ("name", "=", forms_pdf),
            ],
            limit=1,
        )
        self.assertTrue(
            quotation_document, "A new quotation document should be created"
        )
        self.assertFalse(
            quotation_document.company_id,
            "Quotation document shouldn't have a company id",
        )

    def _test_custom_content_kanban_like(self):
        self.start_tour(
            f"/odoo/sales/{self.sale_order.id}",
            "custom_content_kanban_like_tour",
            login="admin",
        )

    def test_quotation_document_is_added_iff_default(self):
        self.assertFalse(self._create_so().quotation_document_ids)

        self.header.add_by_default = True

        self.assertEqual(self._create_so().quotation_document_ids, self.header)

    def test_default_quotation_document_is_added_iff_available(self):
        so_tmpl = self.env["sale.order.template"].create({"name": "Awesome Template"})
        self.header.write(
            {
                "add_by_default": True,
                "quotation_template_ids": [Command.link(so_tmpl.id)],
            }
        )

        sof_without_tmpl = self._create_so_form()
        sof_with_tmpl = self._create_so_form(sale_order_template_id=so_tmpl)

        self.assertFalse(sof_without_tmpl.record.quotation_document_ids)
        self.assertEqual(sof_with_tmpl.record.quotation_document_ids, self.header)

    def test_quotation_document_is_removed_if_unavailable(self):
        so_tmpl = self.env["sale.order.template"].create({"name": "Awesome Template"})
        self.header.write(
            {
                "add_by_default": True,
                "quotation_template_ids": [Command.link(so_tmpl.id)],
            }
        )
        sof = self._create_so_form(sale_order_template_id=so_tmpl)
        self.assertEqual(sof.record.quotation_document_ids, self.header)

        sof.sale_order_template_id = self.env["sale.order.template"]
        sof.save()

        self.assertFalse(sof.record.quotation_document_ids)


@tagged("-at_install", "post_install")
class TestQuotationDocumentBinSize(SaleOrderTemplateCommon):
    def test_check_pdf_validity_under_bin_size(self):
        with file_open(plain_pdf, "rb") as plain_file:
            plain_data = b64encode(plain_file.read())
        document = self.env["quotation.document"].create(
            {
                "name": "header.pdf",
                "datas": plain_data,
                "mimetype": "application/pdf",
                "document_type": "header",
            }
        )
        self.env.flush_all()
        document.invalidate_recordset()

        document.with_context(bin_size=True)._check_pdf_validity()

    def test_check_pdf_validity_still_rejects_encrypted(self):
        with file_open(
            "sale_pdf_quote_builder/tests/files/test_AES.pdf", "rb"
        ) as encrypted_file:
            encrypted = encrypted_file.read()
        with self.assertRaises(ValidationError):
            self.env["quotation.document"].create(
                {
                    "name": "encrypted.pdf",
                    "datas": b64encode(encrypted),
                    "mimetype": "application/pdf",
                    "document_type": "header",
                }
            )
