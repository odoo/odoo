from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


INVOICE_NS = 'http://www.aade.gr/myDATA/invoice/v1.0'
EXPENSE_CLASSIFICATION_NS = 'https://www.aade.gr/myDATA/expensesClassificaton/v1.0'


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestMyDATAReconciliation(AccountTestInvoicingCommon):

    _test_user_groups = None

    @classmethod
    @AccountTestInvoicingCommon.setup_country('gr')
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.write({
            'country_id': cls.env.ref('base.gr').id,
            'vat': '047747210',
        })

    def _create_invoice(self, mark):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2024-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'quantity': 1,
                'price_unit': 100,
            })],
        })
        self.env['l10n_gr_edi.document'].create({
            'move_id': invoice.id,
            'state': 'invoice_sent',
            'mydata_mark': mark,
        })
        return invoice

    @staticmethod
    def _requested_doc(invoice_marks=(), classifications=()):
        root = etree.Element(
            f'{{{INVOICE_NS}}}RequestedDoc',
            nsmap={None: INVOICE_NS, 'ecls': EXPENSE_CLASSIFICATION_NS},
        )
        if invoice_marks:
            invoices_doc = etree.SubElement(root, f'{{{INVOICE_NS}}}invoicesDoc')
            for index, mark in enumerate(invoice_marks, start=1):
                invoice = etree.SubElement(invoices_doc, f'{{{INVOICE_NS}}}invoice')
                etree.SubElement(invoice, f'{{{INVOICE_NS}}}uid').text = f'UID-{mark}'
                etree.SubElement(invoice, f'{{{INVOICE_NS}}}mark').text = mark
                counterpart = etree.SubElement(invoice, f'{{{INVOICE_NS}}}counterpart')
                etree.SubElement(counterpart, f'{{{INVOICE_NS}}}vatNumber').text = '047747210'
                header = etree.SubElement(invoice, f'{{{INVOICE_NS}}}invoiceHeader')
                etree.SubElement(header, f'{{{INVOICE_NS}}}series').text = 'INV'
                etree.SubElement(header, f'{{{INVOICE_NS}}}aa').text = str(index)
                etree.SubElement(header, f'{{{INVOICE_NS}}}issueDate').text = '2024-01-01'
                etree.SubElement(header, f'{{{INVOICE_NS}}}invoiceType').text = '1.1'
                etree.SubElement(header, f'{{{INVOICE_NS}}}currency').text = 'EUR'
                summary = etree.SubElement(invoice, f'{{{INVOICE_NS}}}invoiceSummary')
                etree.SubElement(summary, f'{{{INVOICE_NS}}}totalNetValue').text = '100.00'
                etree.SubElement(summary, f'{{{INVOICE_NS}}}totalVatAmount').text = '24.00'
                etree.SubElement(summary, f'{{{INVOICE_NS}}}totalGrossValue').text = '124.00'
        if classifications:
            classifications_doc = etree.SubElement(root, f'{{{INVOICE_NS}}}expensesClassificationsDoc')
            for invoice_mark, classification_mark, transaction_mode in classifications:
                classification = etree.SubElement(
                    classifications_doc,
                    f'{{{EXPENSE_CLASSIFICATION_NS}}}expensesInvoiceClassification',
                )
                etree.SubElement(
                    classification,
                    f'{{{EXPENSE_CLASSIFICATION_NS}}}invoiceMark',
                ).text = invoice_mark
                etree.SubElement(
                    classification,
                    f'{{{EXPENSE_CLASSIFICATION_NS}}}classificationMark',
                ).text = classification_mark
                etree.SubElement(
                    classification,
                    f'{{{EXPENSE_CLASSIFICATION_NS}}}transactionMode',
                ).text = transaction_mode
        return root

    def test_sync_reconciliation_creates_records(self):
        invoice_1 = self._create_invoice('100')
        invoice_2 = self._create_invoice('101')
        responses = {
            'RequestTransmittedDocs': self._requested_doc(invoice_marks=('100', '101')),
            'RequestDocs': self._requested_doc(),
        }

        def request_documents(company, endpoint, mark):
            yield responses[endpoint]

        with patch.object(self.env.registry['res.company'], '_l10n_gr_edi_request_documents', request_documents):
            self.env.company._l10n_gr_edi_sync_reconciliation()

        reconciliations = self.env['l10n_gr_edi.reconciliation'].search([
            ('company_id', '=', self.env.company.id),
        ], order='mark')
        self.assertRecordValues(reconciliations, [
            {'mark': '100', 'move_id': invoice_1.id, 'partner_id': self.partner_a.id, 'state': 'no_exception'},
            {'mark': '101', 'move_id': invoice_2.id, 'partner_id': self.partner_a.id, 'state': 'no_exception'},
        ])
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_transmitted_mark, '101')
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_counterparty_mark, '0')

    def test_sync_reconciliation_updates_old_invoices_from_new_events(self):
        self._create_invoice('100')
        self._create_invoice('101')
        self._create_invoice('102')
        responses = [
            {
                'RequestTransmittedDocs': self._requested_doc(invoice_marks=('100', '101', '102')),
                'RequestDocs': self._requested_doc(classifications=(('102', '200', '0'),)),
            },
            {
                'RequestTransmittedDocs': self._requested_doc(),
                'RequestDocs': self._requested_doc(classifications=(
                    ('100', '201', '1'),
                    ('101', '202', '2'),
                )),
            },
        ]
        calls = []

        def request_documents(company, endpoint, mark):
            calls.append((endpoint, mark))
            yield responses[(len(calls) - 1) // 2][endpoint]

        with patch.object(self.env.registry['res.company'], '_l10n_gr_edi_request_documents', request_documents):
            self.env.company._l10n_gr_edi_sync_reconciliation()
            self.env.company._l10n_gr_edi_sync_reconciliation()

        reconciliations = self.env['l10n_gr_edi.reconciliation'].search([
            ('company_id', '=', self.env.company.id),
        ], order='mark')
        self.assertRecordValues(reconciliations, [
            {'mark': '100', 'classification_mark': '201', 'state': 'rejected'},
            {'mark': '101', 'classification_mark': '202', 'state': 'deviation'},
            {'mark': '102', 'classification_mark': False, 'state': 'no_exception'},
        ])
        self.assertEqual(calls, [
            ('RequestTransmittedDocs', '0'),
            ('RequestDocs', '0'),
            ('RequestTransmittedDocs', '102'),
            ('RequestDocs', '200'),
        ])
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_counterparty_mark, '202')
