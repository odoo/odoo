# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import datetime
import json
import os

from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import file_open

from odoo.addons.sale.tests.common import SaleCommon

directory = os.path.dirname(__file__)


@tagged('-at_install', 'post_install')
class TestPDFQuoteBuilder(SaleCommon):

    @classmethod
    def setUpClass(cls):
        with freeze_time('2020-10-05 15:15:15'):  # So the validity date is a month later
            super().setUpClass()

            cls.env['quotation.document'].search([]).action_archive()
            cls.env['product.document'].search([]).action_archive()

            with file_open(os.path.join(directory, 'test_pdf', 'test.pdf'), 'rb') as f:
                document = base64.b64encode(f.read())
                IrAttachment = cls.env['ir.attachment']
                attachment_1 = IrAttachment.create({'name': "Header", 'datas': document})
                attachment_2 = IrAttachment.create({'name': "Footer", 'datas': document})
                cls.header, cls.footer = cls.env['quotation.document'].create([{
                    'name': "Header", 'ir_attachment_id': attachment_1.id
                }, {
                    'name': "Footer",
                    'ir_attachment_id': attachment_2.id,
                    'document_type': 'footer',
                }])

                attachment_3 = cls.env['ir.attachment'].create(
                    {'name': "Product Document", 'datas': document}
                )
                cls.product_document = cls.env['product.document'].create({
                    'name': "product doc",
                    'ir_attachment_id': attachment_3.id,
                    'attached_on_sale': 'inside',
                    'res_model': 'product.product',
                    'res_id': cls.product.id,
                })

    def test_compute_customizable_pdf_form_fields_when_no_file(self):
        self.env['quotation.document'].search([]).action_archive()
        self.env['product.document'].search([]).action_archive()
        expected_result = '{"header": {}, "line": {}, "footer": {}}'
        self.sale_order.is_pdf_quote_builder_active = True
        self.assertEqual(self.sale_order.customizable_pdf_form_fields, expected_result)

    def test_compute_customizable_pdf_form_fields_with_1_file(self):
        self.sale_order.order_line[0].product_id = self.product.id
        quotation_custom_form_fields = {  # 2 times the same doc
            "custom_1": "",
            "custom_2": "",
            "description": "",  # already mapped for product_document
            "dyna_1": "",
            "dyna_2": "",
            "quantity": "",  # already mapped for product_document
        }
        product_custom_form_fields = {
            'custom_1': '', 'custom_2': '', 'dyna_1': '', 'dyna_2': '',
        }
        expected_result = {
            "header": {str(self.header.id): {
                "document_name": "Header", "custom_form_fields": quotation_custom_form_fields
            }},
            "line": {
                str(self.sale_order.order_line[0].id): {
                    "product_name": "Test Product",
                    str(self.product_document.id): {
                        "document_name": "product doc",
                        "custom_form_fields": product_custom_form_fields
                    }
                }
            },
            "footer": {str(self.footer.id): {
                "document_name": "Footer", "custom_form_fields": quotation_custom_form_fields
            }}
        }
        self.sale_order.is_pdf_quote_builder_active = True
        computed_result = json.loads(self.sale_order.customizable_pdf_form_fields)
        # Compare part of it as we reach the maximum chars to compare
        self.assertEqual(computed_result['header'], expected_result['header'])
        self.assertEqual(computed_result['line'], expected_result['line'])
        self.assertEqual(computed_result['footer'], expected_result['footer'])

    def test_dynamic_fields_mapping_for_quotation_document(self):
        FormField = self.env['sale.pdf.form.field']
        doc_type = 'quotation_document'
        new_form_fields = FormField.create([
            {'name': "boolean_test", 'document_type': doc_type, 'path': 'locked'},
            {'name': "char_test", 'document_type': doc_type, 'path': 'name'},
            {'name': "date_test", 'document_type': doc_type, 'path': 'validity_date'},
            {'name': "datetime_test", 'document_type': doc_type, 'path': 'commitment_date'},
            {'name': "float_test", 'document_type': doc_type, 'path': 'prepayment_percent'},
            {'name': "integer_test", 'document_type': doc_type, 'path': 'company_id.color'},
            {'name': "selection_test", 'document_type': doc_type, 'path': 'state'},
            {'name': "monetary_test", 'document_type': doc_type, 'path': 'amount_total'},

            {'name': "one2many_test", 'document_type': doc_type, 'path': 'order_line'},
            {'name': "many2one_test", 'document_type': doc_type, 'path': 'company_id'},
            {'name': "many2many_test", 'document_type': doc_type, 'path': 'company_id.parent_ids'},
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
        FormField = self.env['sale.pdf.form.field']
        doc_type = 'product_document'
        new_form_fields = FormField.create([
            {'name': "boolean_test", 'document_type': doc_type, 'path': 'order_id.locked'},
            {'name': "char_test", 'document_type': doc_type, 'path': 'order_id.name'},
            {'name': "date_test", 'document_type': doc_type, 'path': 'order_id.validity_date'},
            {'name': "dt_test", 'document_type': doc_type, 'path': 'order_id.commitment_date'},
            {'name': "float_test", 'document_type': doc_type, 'path': 'discount'},
            {'name': "integer_test", 'document_type': doc_type, 'path': 'sequence'},
            {'name': "selection_test", 'document_type': doc_type, 'path': 'order_id.state'},
            {'name': "monetary_test", 'document_type': doc_type, 'path': 'order_id.amount_total'},

            {'name': "one2many_test", 'document_type': doc_type, 'path': 'order_id.order_line'},
            {'name': "many2one_test", 'document_type': doc_type, 'path': 'order_id.company_id'},
            {'name': "many2many_test", 'document_type': doc_type, 'path': 'tax_id'},
        ])
        sol_1, sol_2 = self.sale_order.order_line
        sol_1.update({
            'discount': 4.99, 'tax_id': [
                Command.create({'name': 'test tax'}), Command.create({'name': 'test tax2'})
            ]
        })
        self.sale_order.commitment_date = datetime.datetime(2121, 12, 21, 12, 21, 12)
        form_field_expected_value_map = {
            new_form_fields[0]: "No",  # boolean
            new_form_fields[1]: self.sale_order.name,  # char
            new_form_fields[2]: "11/04/2020",  # date
            new_form_fields[3]: "Dec 21, 2121, 1:21:12 PM",  # datetime
            new_form_fields[4]: "4.99",  # float
            new_form_fields[5]: "10",  # integer
            new_form_fields[6]: "Quotation",  # selection
            new_form_fields[7]: "$\xa0720.01",  # monetary

            new_form_fields[8]: f"{sol_1.display_name}, {sol_2.display_name}",  # one2many
            new_form_fields[9]: f"{self.sale_order.company_id.display_name}",  # many2one
            new_form_fields[10]: "test tax, test tax2",  # many2many
        }
        for form_field, expected_value in form_field_expected_value_map.items():
            result = self.env['ir.actions.report']._get_value_from_path(
                form_field, self.sale_order, sol_1
            )
            self.assertEqual(result, expected_value)
