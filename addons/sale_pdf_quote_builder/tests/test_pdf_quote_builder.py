# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from base64 import b64encode
from functools import partial
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import file_open

from odoo.addons.base.tests.common import BaseUsersCommon
from odoo.addons.sale_management.tests.common import SaleManagementCommon
from odoo.addons.sale_pdf_quote_builder.controllers.quotation_document import (
    QuotationDocumentController
)
from .files import forms_pdf, plain_pdf


@tagged('-at_install', 'post_install')
class TestPDFQuoteBuilder(BaseUsersCommon, SaleManagementCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.QuotationDocumentController = QuotationDocumentController()

        cls.sale_order.validity_date = '2020-11-04'
        cls.sale_order.partner_id.tz = 'Europe/Brussels'
        cls.env['product.document'].search([]).action_archive()
        cls.env['quotation.document'].search([]).action_archive()

        with file_open(forms_pdf, 'rb') as file:
            forms_pdf_data = b64encode(file.read())

        with file_open(plain_pdf, 'rb') as file:
            plain_pdf_data = b64encode(file.read())

        att_header, att_footer, att_prod_doc = cls.env['ir.attachment'].create([{
            'name': "Header",
            'datas': plain_pdf_data,
        }, {
            'name': "Footer",
            'datas': forms_pdf_data,
        }, {
            'name': "Product Document",
            'datas': forms_pdf_data,
        }])
        cls.header, cls.footer = cls.env['quotation.document'].create([{
            'name': "Header",
            'ir_attachment_id': att_header.id,
            'document_type': 'header',
        }, {
            'name': "Footer",
            'ir_attachment_id': att_footer.id,
            'document_type': 'footer',
        }])
        cls.product_document = cls.env['product.document'].create({
            'name': "Product Document",
            'ir_attachment_id': att_prod_doc.id,
            'attached_on_sale': 'inside',
            'res_model': 'product.product',
            'res_id': cls.product.id,
        })

        cls.alt_company = cls.env['res.company'].create({'name': "Backup Company"})

    def test_compute_customizable_pdf_form_fields_when_no_file(self):
        self.env['quotation.document'].search([]).action_archive()
        self.env['product.document'].search([]).action_archive()
        self.assertEqual(self.sale_order.customizable_pdf_form_fields, False)

    def test_dynamic_fields_mapping_for_quotation_document(self):
        FormField = self.env['sale.pdf.form.field']
        new_form_field = partial(dict, document_type='quotation_document')
        new_form_fields = FormField.create([
            new_form_field(name="boolean_test", path='locked'),
            new_form_field(name="char_test", path='name'),
            new_form_field(name="date_test", path='validity_date'),
            new_form_field(name="datetime_test", path='commitment_date'),
            new_form_field(name="float_test", path='prepayment_percent'),
            new_form_field(name="integer_test", path='company_id.color'),
            new_form_field(name="selection_test", path='state'),
            new_form_field(name="monetary_test", path='amount_total'),

            new_form_field(name="one2many_test", path='order_line'),
            new_form_field(name="many2one_test", path='company_id'),
            new_form_field(name="many2many_test", path='company_id.parent_ids'),
        ])
        sol_1, sol_2 = self.sale_order.order_line
        form_field_expected_value_map = {
            new_form_fields[0]: "No",  # boolean
            new_form_fields[1]: self.sale_order.name,  # char
            new_form_fields[2]: "11/04/2020",  # date
            new_form_fields[3]: "",  # datetime missing
            new_form_fields[4]: "1.0",  # float
            new_form_fields[5]: "1",  # integer
            new_form_fields[6]: "Quotation",  # selection
            new_form_fields[7]: "$\xa0725.00",  # monetary

            new_form_fields[8]: f"{sol_1.display_name}, {sol_2.display_name}",  # one2many
            new_form_fields[9]: f"{self.sale_order.company_id.display_name}",  # many2one
            new_form_fields[10]: f"{self.sale_order.company_id.display_name}",  # many2many
        }
        for form_field, expected_value in form_field_expected_value_map.items():
            result = self.env['ir.actions.report']._get_value_from_path(
                form_field, self.sale_order
            )
            self.assertEqual(result, expected_value)

    def test_dynamic_fields_mapping_for_product_document(self):
        self.sale_order.commitment_date = '2121-12-21 12:21:12'
        sol_1, sol_2 = self.sale_order.order_line
        sol_1.update({
            'discount': 4.99,
            'tax_id': [
                Command.create({'name': "test tax1"}),
                Command.create({'name': "test tax2"}),
            ],
        })
        new_form_field = partial(dict, document_type='product_document')
        new_form_fields = self.env['sale.pdf.form.field'].create([
            new_form_field(name="boolean_test", path='order_id.locked'),
            new_form_field(name="char_test", path='order_id.name'),
            new_form_field(name="date_test", path='order_id.validity_date'),
            new_form_field(name="datetime_test", path='order_id.commitment_date'),
            new_form_field(name="float_test", path='discount'),
            new_form_field(name="integer_test", path='sequence'),
            new_form_field(name="selection_test", path='order_id.state'),
            new_form_field(name="monetary_test", path='order_id.amount_total'),

            new_form_field(name="one2many_test", path='order_id.order_line'),
            new_form_field(name="many2one_test", path='order_id.company_id'),
            new_form_field(name="many2many_test", path='tax_id'),
        ])
        expected = {
            'boolean_test': "No",
            'char_test': self.sale_order.name,
            'date_test': "11/04/2020",
            'datetime_test': "12/21/2121 13:21:12",
            'float_test': "4.99",
            'integer_test': "10",
            'selection_test': "Quotation",
            'monetary_test': self.sale_order.currency_id.format(720.01),

            'one2many_test': f"{sol_1.display_name}, {sol_2.display_name}",
            'many2one_test': self.sale_order.company_id.display_name,
            'many2many_test': "test tax1, test tax2",
        }
        for form_field in new_form_fields:
            result = self.env['ir.actions.report']._get_value_from_path(
                form_field, self.sale_order, sol_1
            )
            self.assertEqual(result, expected[form_field.name])

    def test_product_document_dialog_params_access(self):
        sale_order_user_internal = self.sale_order.copy({'user_id': self.user_internal.id})
        dialog_param = sale_order_user_internal.with_user(
            self.user_internal.id
        ).get_update_included_pdf_params()
        # should return all document data regardless of access
        self.assertEqual('Header', dialog_param['headers']['files'][0]['name'])
        self.assertEqual('Product > Test Product', dialog_param['lines'][0]['name'])

    def test_quotation_document_upload_no_template(self):
        """Check that uploading quotation documents get assigned the active company."""
        if 'website' not in self.env:
            self.skipTest("Module `website` not found")
        else:
            from odoo.addons.website.tools import MockRequest  # noqa: PLC0415

        allowed_company_ids = [self.alt_company.id, self.env.company.id]

        # Upload document without Sale Order Template
        with (
            MockRequest(self.env) as request,
            file_open(plain_pdf, 'rb') as file,
            patch.object(request.httprequest.files, 'getlist', lambda _key: [FileStorage(file)]),
        ):
            request.params['allowed_company_ids'] = json.dumps(allowed_company_ids)
            res = self.QuotationDocumentController.upload_document(ufile=FileStorage(file))
            self.assertEqual(res.status_code, 200, "Upload should be successful")

        quotation_document = self.env['quotation.document'].search([
            ('name', '=', plain_pdf),
        ], limit=1)
        self.assertTrue(quotation_document, "A new quotation document should be created")
        self.assertEqual(
            quotation_document.company_id,
            self.alt_company,
            "Quotation document company should be the currently active company",
        )

    def test_quotation_document_upload_for_template(self):
        """Check that uploading quotation documents get assigned the the quotation company."""
        if 'website' not in self.env:
            self.skipTest("Module `website` not found")
        else:
            from odoo.addons.website.tools import MockRequest  # noqa: PLC0415

        allowed_company_ids = [self.alt_company.id, self.env.company.id]

        # Upload a document for a Sale Order Template without company id
        self.empty_order_template.company_id = False
        with (
            MockRequest(self.env) as request,
            file_open(forms_pdf, 'rb') as file,
            patch.object(request.httprequest.files, 'getlist', lambda _key: [FileStorage(file)]),
        ):
            request.params['allowed_company_ids'] = json.dumps(allowed_company_ids)
            res = self.QuotationDocumentController.upload_document(
                ufile=FileStorage(file),
                sale_order_template_id=str(self.empty_order_template.id),
            )
            self.assertEqual(res.status_code, 200, "Upload should be successful")

        quotation_document = self.env['quotation.document'].search([
            ('name', '=', forms_pdf),
        ], limit=1)
        self.assertTrue(quotation_document, "A new quotation document should be created")
        self.assertFalse(
            quotation_document.company_id,
            "Quotation document shouldn't have a company id",
        )

    def _test_custom_content_kanban_like(self):
        # TODO VCR finish tour and uncomment
        self.start_tour(
            f'/odoo/sales/{self.sale_order.id}',
            'custom_content_kanban_like_tour',
            login='admin',
        )
        # Assert documents are selected
