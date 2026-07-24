from urllib.parse import parse_qsl, urlsplit

from lxml import etree

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import MockHTTPClient, tagged

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
        cls.env.company.write({
            'l10n_gr_edi_aade_id': 'test_user',
            'l10n_gr_edi_aade_key': 'test_key',
        })

    def setUp(self):
        super().setUp()
        self.responses = {'RequestTransmittedDocs': [], 'RequestDocs': []}
        self.mydata = self.enterContext(MockHTTPClient(
            url='https://mydataapidev.aade.gr',
            method='GET',
            return_status=lambda request: self._next_response(request)[0],
            return_body=lambda request: self._next_response(request)[1],
        ))

    def _next_response(self, request):
        # return_status and return_body are both called for the same request, only consume one page
        if getattr(request, '_mydata_response', None) is None:
            status, body = self.responses[self._get_endpoint(request)].pop(0)
            if not isinstance(body, bytes):
                body = etree.tostring(body)
            request._mydata_response = (status, body)
        return request._mydata_response

    @staticmethod
    def _get_endpoint(request):
        return urlsplit(request.url).path.rsplit('/', 1)[-1]

    def _get_mydata_calls(self):
        return [
            (self._get_endpoint(request), dict(parse_qsl(urlsplit(request.url).query)))
            for request in self.mydata.calls
        ]

    def _get_reconciliations(self):
        return self.env['l10n_gr_edi.reconciliation'].search([
            ('company_id', '=', self.env.company.id),
        ], order='mark')

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
    def _requested_doc(invoice_marks=(), classifications=(), continuation=None):
        root = etree.Element(
            f'{{{INVOICE_NS}}}RequestedDoc',
            nsmap={None: INVOICE_NS, 'ecls': EXPENSE_CLASSIFICATION_NS},
        )
        if continuation:
            next_partition_key, next_row_key = continuation
            token = etree.SubElement(root, f'{{{INVOICE_NS}}}continuationToken')
            etree.SubElement(token, f'{{{INVOICE_NS}}}nextPartitionKey').text = next_partition_key
            etree.SubElement(token, f'{{{INVOICE_NS}}}nextRowKey').text = next_row_key
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
        self.responses['RequestTransmittedDocs'].append((200, self._requested_doc(invoice_marks=('100', '101'))))
        self.responses['RequestDocs'].append((200, self._requested_doc()))

        self.env.company._l10n_gr_edi_sync_reconciliation()

        self.assertRecordValues(self._get_reconciliations(), [
            {'mark': '100', 'move_id': invoice_1.id, 'partner_id': self.partner_a.id, 'state': 'no_exception'},
            {'mark': '101', 'move_id': invoice_2.id, 'partner_id': self.partner_a.id, 'state': 'no_exception'},
        ])
        self.assertEqual(self._get_mydata_calls(), [
            ('RequestTransmittedDocs', {'mark': '0'}),
            ('RequestDocs', {'mark': '0'}),
        ])
        for request in self.mydata.calls:
            self.assertEqual(request.headers['aade-user-id'], 'test_user')
            self.assertEqual(request.headers['ocp-apim-subscription-key'], 'test_key')
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_transmitted_mark, '101')
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_counterparty_mark, '0')

    def test_sync_reconciliation_updates_old_invoices_from_new_events(self):
        self._create_invoice('100')
        self._create_invoice('101')
        self._create_invoice('102')
        self.responses['RequestTransmittedDocs'] += [
            (200, self._requested_doc(invoice_marks=('100', '101', '102'))),
            (200, self._requested_doc()),
        ]
        self.responses['RequestDocs'] += [
            (200, self._requested_doc(classifications=(('102', '200', '0'),))),
            (200, self._requested_doc(classifications=(
                ('100', '201', '1'),
                ('101', '202', '2'),
            ))),
        ]

        self.env.company._l10n_gr_edi_sync_reconciliation()
        self.env.company._l10n_gr_edi_sync_reconciliation()

        self.assertRecordValues(self._get_reconciliations(), [
            {'mark': '100', 'classification_mark': '201', 'state': 'rejected'},
            {'mark': '101', 'classification_mark': '202', 'state': 'deviation'},
            {'mark': '102', 'classification_mark': False, 'state': 'no_exception'},
        ])
        self.assertEqual(self._get_mydata_calls(), [
            ('RequestTransmittedDocs', {'mark': '0'}),
            ('RequestDocs', {'mark': '0'}),
            ('RequestTransmittedDocs', {'mark': '102'}),
            ('RequestDocs', {'mark': '200'}),
        ])
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_counterparty_mark, '202')

    def test_sync_reconciliation_pagination(self):
        self._create_invoice('100')
        self._create_invoice('101')
        self._create_invoice('102')
        self.responses['RequestTransmittedDocs'] += [
            (200, self._requested_doc(invoice_marks=('100', '101'), continuation=('pk-1', 'rk-1'))),
            (200, self._requested_doc(invoice_marks=('102',))),
        ]
        self.responses['RequestDocs'] += [
            (200, self._requested_doc(classifications=(('100', '201', '1'),), continuation=('pk-2', 'rk-2'))),
            (200, self._requested_doc(classifications=(('101', '202', '2'),))),
        ]

        self.env.company._l10n_gr_edi_sync_reconciliation()

        self.assertEqual(self._get_mydata_calls(), [
            ('RequestTransmittedDocs', {'mark': '0'}),
            ('RequestTransmittedDocs', {'mark': '0', 'nextPartitionKey': 'pk-1', 'nextRowKey': 'rk-1'}),
            ('RequestDocs', {'mark': '0'}),
            ('RequestDocs', {'mark': '0', 'nextPartitionKey': 'pk-2', 'nextRowKey': 'rk-2'}),
        ])
        self.assertRecordValues(self._get_reconciliations(), [
            {'mark': '100', 'classification_mark': '201', 'state': 'rejected'},
            {'mark': '101', 'classification_mark': '202', 'state': 'deviation'},
            {'mark': '102', 'classification_mark': False, 'state': 'no_exception'},
        ])
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_transmitted_mark, '102')
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_counterparty_mark, '202')

    def test_sync_reconciliation_invalid_responses(self):
        for status, body in (
            (500, b''),
            (200, b'not xml'),
            (200, b'<ResponseDoc/>'),
        ):
            with self.subTest(status=status, body=body):
                self.responses['RequestTransmittedDocs'] = [(status, body)]
                with self.assertRaisesRegex(UserError, 'Could not retrieve documents from myDATA.'):
                    self.env.company._l10n_gr_edi_sync_reconciliation()
                self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_transmitted_mark, '0')

    def test_sync_reconciliation_pagination_failure(self):
        self._create_invoice('100')
        self.responses['RequestTransmittedDocs'] += [
            (200, self._requested_doc(invoice_marks=('100',), continuation=('pk-1', 'rk-1'))),
            (500, b''),
        ]

        with self.assertRaisesRegex(UserError, 'Could not retrieve documents from myDATA.'):
            self.env.company._l10n_gr_edi_sync_reconciliation()

        # The first page was processed before the second one failed, but everything is rolled back with the error
        self.assertEqual(len(self.mydata.calls), 2)
        self.assertFalse(self._get_reconciliations())
        self.assertEqual(self.env.company.l10n_gr_edi_reconciliation_transmitted_mark, '0')
