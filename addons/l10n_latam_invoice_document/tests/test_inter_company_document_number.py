# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest

from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestInterCompanyDocumentNumber(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if 'intercompany_generate_bills_refund' not in cls.env['res.company']._fields:
            raise unittest.SkipTest('account_inter_company_rules is not installed')

        cls.company_a = cls.company_data['company']
        cls.company_b = cls.setup_other_company(name='Company B')['company']
        (cls.company_a + cls.company_b).write({'intercompany_generate_bills_refund': True, 'intercompany_document_state': 'posted'})

        cls.document_type = cls.env['l10n_latam.document.type'].create({
            'name': 'INVOICES A',
            'doc_code_prefix': 'FA-A',
            'country_id': cls.company_b.account_fiscal_country_id.id,
            'internal_type': 'invoice',
        })

        purchase_journal = cls.env['account.journal'].search([
            ('type', '=', 'purchase'), ('company_id', '=', cls.company_b.id),
        ], limit=1)
        purchase_journal.l10n_latam_use_documents = True

    def test_inter_company_bill_document_number(self):
        """
        Ensure that posting a customer invoice in company A whose partner is company B will create
        a vendor bill in company B that inherits the source invoice's l10n_latam_document_number.
        """
        customer_invoice = self.env['account.move'].with_company(self.company_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.company_b.partner_id.id,
            'invoice_date': '2023-05-01',
            'l10n_latam_document_type_id': self.document_type.id,
            'l10n_latam_document_number': '00001-00000123',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1.0,
            })],
        })
        customer_invoice.action_post()

        supplier_bill = self.env['account.move'].search([
            ('auto_invoice_id', '=', customer_invoice.id),
        ])
        self.assertTrue(
            supplier_bill.l10n_latam_document_number,
            'The auto-generated vendor bill should have inherited a document number from the source invoice.'
        )
