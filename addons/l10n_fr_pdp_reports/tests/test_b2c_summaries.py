from base64 import b64decode

from lxml import etree

from odoo import Command, fields
from odoo.tests.common import tagged

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpB2CSummaries(PdpTestCommon):
    def test_summary_split_by_category(self):
        """B2C summary must be split per category when goods and services are present."""
        day = fields.Date.from_string('2025-02-01')
        service_product = self.env['product.product'].create({
            'name': "Test Service",
            'type': 'service',
            'lst_price': 80,
            'taxes_id': [Command.set(self.tax_20.ids)],
            'company_id': self.company.id,
            'property_account_income_id': self.income_account.id,
        })
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2c.id,
            'invoice_date': day,
            'journal_id': journal.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                    'account_id': self.income_account.id,
                }),
                Command.create({
                    'product_id': service_product.id,
                    'quantity': 1,
                    'price_unit': 80,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                    'account_id': self.income_account.id,
                }),
            ],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._run_aggregation().filtered(lambda f: f.report_kind == 'transaction')[:1]
        xml = etree.fromstring(b64decode(flow.payload))
        summaries = xml.findall('.//TransactionsReport/Transactions')
        categories = {summary.findtext('CategoryCode') for summary in summaries}
        self.assertIn('TLB1', categories, 'Goods summary should use TLB1')
        self.assertIn('TPS1', categories, 'Services summary should use TPS1')

    def test_summary_vat_breakdown_present(self):
        """B2C summary must include VAT breakdown and amounts."""
        day = fields.Date.from_string('2025-02-01')
        self._create_invoice(date_val=day, sent=True)
        flows = self._run_aggregation()
        flow = flows.filtered(lambda f: f.report_kind == 'transaction')
        payload_b64 = flow.payload
        xml = etree.fromstring(b64decode(payload_b64))
        summary = xml.find('.//TransactionsReport/Transactions')
        self.assertIsNotNone(summary, 'Transactions summary block missing')
        vat_lines = summary.findall('./TaxSubtotal')
        self.assertTrue(vat_lines, 'VAT breakdown missing in summary')
        # Amount fields must be present
        for node in vat_lines:
            taxable = node.find('TaxableAmount')
            tax = node.find('TaxTotal')
            self.assertIsNotNone(taxable, 'TaxableAmount missing in VAT bucket')
            self.assertIsNotNone(tax, 'TaxTotal missing in VAT bucket')

    def test_tma1_summary_omits_transactions_count(self):
        """TT-85 should be omitted for TMA1 summaries (optional per spec)."""
        day = fields.Date.from_string('2025-02-01')
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        tax_group = self.tax_20.tax_group_id
        margin_tax = self.env['account.tax'].create({
            'name': 'VAT 20 Margin',
            'amount': 20,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': self.company.id,
            'tax_group_id': tax_group.id,
            'l10n_fr_pdp_tt81_category': 'TMA1',
        })
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2c.id,
            'invoice_date': day,
            'journal_id': journal.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'quantity': 1,
                'price_unit': 100,
                'tax_ids': [Command.set(margin_tax.ids)],
                'account_id': self.income_account.id,
            })],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._run_aggregation().filtered(lambda f: f.report_kind == 'transaction')[:1]
        xml = etree.fromstring(b64decode(flow.payload))
        summary = xml.find(".//TransactionsReport/Transactions[CategoryCode='TMA1']")
        self.assertIsNotNone(summary, 'TMA1 summary should be present')
        self.assertIsNone(
            summary.find('TransactionsCount'),
            'TransactionsCount must be omitted for TMA1 summaries.',
        )

    def test_summary_regularization_keeps_net_amounts(self):
        """Regularization invoices with negative lines must stay net in 10.3."""
        day = fields.Date.from_string('2025-02-01')
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company.id),
        ], limit=1)
        move = self.env['account.move'].with_company(self.company.id).create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b2c.id,
            'invoice_date': day,
            'journal_id': journal.id,
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.service_product.id,
                    'quantity': 1,
                    'price_unit': 100,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                    'account_id': self.income_account.id,
                }),
                Command.create({
                    'product_id': self.service_product.id,
                    'quantity': 1,
                    'price_unit': -40,
                    'tax_ids': [Command.set(self.tax_20.ids)],
                    'account_id': self.income_account.id,
                }),
            ],
        })
        move.action_post()
        move.is_move_sent = True

        flow = self._run_aggregation().filtered(lambda f: f.report_kind == 'transaction')[:1]
        xml = etree.fromstring(b64decode(flow.payload))
        summary = xml.find(".//TransactionsReport/Transactions[CategoryCode='TPS1']")
        self.assertIsNotNone(summary, 'TPS1 summary should be present')
        self.assertEqual(summary.findtext('TaxExclusiveAmount'), '60.0')
        self.assertEqual(summary.findtext('TaxTotal'), '12.0')
