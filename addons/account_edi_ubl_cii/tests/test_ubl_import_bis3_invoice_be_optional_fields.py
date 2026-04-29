from odoo.fields import Date
from odoo.addons.account_edi_ubl_cii.tools.ubl_20_optional_fields import PEPPOL_INVOICE_OPTIONAL_FIELDS, PEPPOL_INVOICE_OPTIONAL_LINE_FIELDS, PEPPOL_CREDIT_NOTE_OPTIONAL_FIELDS, PEPPOL_CREDIT_NOTE_OPTIONAL_LINE_FIELDS
from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEOptionalFields(TestUblImportBis3InvoiceBE):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_import_invoice_optional_fields(self):
        # create the account.move fields.
        model_id = self.env["ir.model"]._get_id("account.move")
        self.env["ir.model.fields"].create([{
                "name": field_name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": field_config.get('type'),
                "state": "manual",
            }
            for field_name, field_config in PEPPOL_INVOICE_OPTIONAL_FIELDS.items()
        ])

        # create the account.move.line fields.
        model_id = self.env["ir.model"]._get_id("account.move.line")
        self.env["ir.model.fields"].create([{
                "name": field_name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": field_config.get('type'),
                "state": "manual",
            }
            for field_name, field_config in PEPPOL_INVOICE_OPTIONAL_LINE_FIELDS.items()
        ])

        # create the invoice
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_invoice_optional_fields',
            journal=self.company_data['default_journal_purchase'],
        )

        self.assertRecordValues(invoice, [{
            'x_studio_peppol_tax_point_date': Date.from_string('2026-02-28'),
            'x_studio_peppol_contract_document_reference_id': 'whatever_peppol_contract_document_reference_id',
            'x_studio_peppol_despatch_document_reference_id': 'whatever_peppol_despatch_document_reference_id',
            'x_studio_peppol_accounting_cost': '123',
            'x_studio_peppol_order_reference_id': 'whatever_peppol_order_reference_id',
            'x_studio_peppol_invoice_period_start_date': Date.from_string('2026-02-27'),
            'x_studio_peppol_invoice_period_end_date': Date.from_string('2026-02-28'),
            'x_studio_peppol_project_reference_id': 'whatever_project_reference_id',
        }])

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'x_studio_peppol_order_line_reference_id': 'whatever_order_line_reference_id',
            'x_studio_peppol_buyers_item_id': 'whatever_buyers_item_id',
        }])

    def test_import_credit_note_with_optional_fields(self):
        # create the account.move fields.
        model_id = self.env["ir.model"]._get_id("account.move")
        self.env["ir.model.fields"].create([{
                "name": field_name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": field_config.get('type'),
                "state": "manual",
            }
            for field_name, field_config in PEPPOL_CREDIT_NOTE_OPTIONAL_FIELDS.items()
        ])

        # create the account.move.line fields.
        model_id = self.env["ir.model"]._get_id("account.move.line")
        self.env["ir.model.fields"].create([{
                "name": field_name,
                "model": "account.move",
                "model_id": model_id,
                "ttype": field_config.get('type'),
                "state": "manual",
            }
            for field_name, field_config in PEPPOL_CREDIT_NOTE_OPTIONAL_LINE_FIELDS.items()
        ])

        # create the invoice
        invoice = self._import_invoice_as_attachment_on(
            test_name='test_import_credit_note_optional_fields',
            journal=self.company_data['default_journal_purchase'],
        )

        self.assertRecordValues(invoice, [{
            'x_studio_peppol_tax_point_date': Date.from_string('2026-02-28'),
            'x_studio_peppol_contract_document_reference_id': 'whatever_peppol_contract_document_reference_id',
            'x_studio_peppol_despatch_document_reference_id': 'whatever_peppol_despatch_document_reference_id',
            'x_studio_peppol_accounting_cost': '123',
            'x_studio_peppol_order_reference_id': 'whatever_peppol_order_reference_id',
            'x_studio_peppol_invoice_period_start_date': Date.from_string('2026-02-27'),
            'x_studio_peppol_invoice_period_end_date': Date.from_string('2026-02-28'),
        }])

        self.assertRecordValues(invoice.invoice_line_ids, [{
            'x_studio_peppol_order_line_reference_id': 'whatever_order_line_reference_id',
            'x_studio_peppol_buyers_item_id': 'whatever_buyers_item_id',
        }])
