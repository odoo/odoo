# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager

from odoo.tests import tagged
from odoo.tests.common import freeze_time

from .common import TestEsEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSiiJournalDashboard(TestEsEdiCommon):

    def _create_sii_move(self, journal, partner, invoice_date, taxes, move_type='out_invoice'):
        return self._create_invoice_one_line(
            move_type=move_type,
            journal_id=journal,
            partner_id=partner,
            invoice_date=invoice_date,
            product_id=self.product_a,
            tax_ids=taxes,
            post=True,
        )

    @freeze_time('2019-01-10 12:00:00')
    def test_sii_dashboard_compute_fields_and_sql(self):
        sale_journal = self.company_data['default_journal_sale']
        purchase_journal = self.company_data['default_journal_purchase']
        sale_tax = self._get_tax_by_xml_id('s_iva21b')
        purchase_tax = self._get_tax_by_xml_id('p_iva21_bc')
        no_tax = self.env['account.tax']
        outside_eu_partner = self.env['res.partner'].create({
            'name': 'Outside EU Vendor',
            'country_id': self.env.ref('base.us').id,
        })

        error_invoice = self._create_sii_move(sale_journal, self.partner_b, '2019-01-10', sale_tax)
        self.env['l10n_es_edi_sii.document'].sudo().create({
            'move_id': error_invoice.id,
            'state': 'to_send',
            'response_message': 'Still failing',
        })

        sent_invoice = self._create_sii_move(sale_journal, self.partner_b, '2019-01-10', sale_tax)
        self.env['l10n_es_edi_sii.document'].sudo().create({
            'move_id': sent_invoice.id,
            'state': 'accepted',
            'csv': 'CSV-SENT',
        })

        latest_csv_invoice = self._create_sii_move(sale_journal, self.partner_b, '2019-01-10', sale_tax)
        self.env['l10n_es_edi_sii.document'].sudo().create([
            {
                'move_id': latest_csv_invoice.id,
                'state': 'accepted',
                'csv': 'CSV-ACCEPTED',
            },
            {
                'move_id': latest_csv_invoice.id,
                'state': 'to_send',
                'csv': 'CSV-LATEST',
                'response_message': 'Retry pending',
            },
        ])

        urgent_invoice = self._create_sii_move(sale_journal, self.partner_b, '2019-01-01', sale_tax)
        outside_eu_bill_without_taxes = self._create_sii_move(purchase_journal, outside_eu_partner, '2019-01-10', no_tax, 'in_invoice')
        outside_eu_bill_with_taxes = self._create_sii_move(purchase_journal, outside_eu_partner, '2019-01-10', purchase_tax, 'in_invoice')
        eu_recent_bill_without_taxes = self._create_sii_move(purchase_journal, self.partner_a, '2019-01-10', no_tax, 'in_invoice')
        eu_late_bill_without_taxes = self._create_sii_move(purchase_journal, self.partner_a, '2019-01-01', no_tax, 'in_invoice')
        eu_very_late_bill_without_taxes = self._create_sii_move(purchase_journal, self.partner_a, '2018-10-01', no_tax, 'in_invoice')

        moves = (
            error_invoice
            | sent_invoice
            | latest_csv_invoice
            | urgent_invoice
            | outside_eu_bill_without_taxes
            | outside_eu_bill_with_taxes
            | eu_recent_bill_without_taxes
            | eu_late_bill_without_taxes
            | eu_very_late_bill_without_taxes
        )
        moves.invalidate_recordset([
            'l10n_es_edi_is_required',
            'l10n_es_edi_sii_state',
            'l10n_es_edi_csv',
            'l10n_es_edi_sii_error',
        ])

        self.assertEqual(error_invoice.l10n_es_edi_sii_state, 'to_send')
        self.assertFalse(error_invoice.l10n_es_edi_csv)
        self.assertIn('Still failing', error_invoice.l10n_es_edi_sii_error)
        self.assertEqual(sent_invoice.l10n_es_edi_sii_state, 'sent')
        self.assertEqual(sent_invoice.l10n_es_edi_csv, 'CSV-SENT')
        self.assertFalse(sent_invoice.l10n_es_edi_sii_error)
        self.assertEqual(latest_csv_invoice.l10n_es_edi_sii_state, 'to_send')
        self.assertEqual(latest_csv_invoice.l10n_es_edi_csv, 'CSV-LATEST')
        self.assertIn('Retry pending', latest_csv_invoice.l10n_es_edi_sii_error)
        self.assertEqual(urgent_invoice.l10n_es_edi_sii_state, 'to_send')
        self.assertFalse(urgent_invoice.l10n_es_edi_sii_error)
        self.assertFalse(outside_eu_bill_without_taxes.l10n_es_edi_is_required)
        self.assertFalse(outside_eu_bill_without_taxes.l10n_es_edi_sii_state)
        self.assertTrue(outside_eu_bill_with_taxes.l10n_es_edi_is_required)
        self.assertEqual(outside_eu_bill_with_taxes.l10n_es_edi_sii_state, 'to_send')
        self.assertTrue(eu_recent_bill_without_taxes.l10n_es_edi_is_required)
        self.assertEqual(eu_recent_bill_without_taxes.l10n_es_edi_sii_state, 'to_send')
        self.assertTrue(eu_late_bill_without_taxes.l10n_es_edi_is_required)
        self.assertEqual(eu_late_bill_without_taxes.l10n_es_edi_sii_state, 'to_send')
        self.assertTrue(eu_very_late_bill_without_taxes.l10n_es_edi_is_required)
        self.assertEqual(eu_very_late_bill_without_taxes.l10n_es_edi_sii_state, 'to_send')

        journals = sale_journal | purchase_journal
        journals.invalidate_recordset(['l10n_es_sii_pending_count', 'l10n_es_sii_kanban_state'])
        queries = []
        with contextmanager(lambda: self._patchExecute(queries))():
            dashboard_data = journals._get_journal_dashboard_data_batched()

        self.assertEqual(dashboard_data[sale_journal.id]['l10n_es_sii_pending_count'], 3)
        self.assertEqual(dashboard_data[sale_journal.id]['l10n_es_sii_kanban_state'], 'urgent')
        self.assertEqual(dashboard_data[sale_journal.id]['l10n_es_sii_state_color'], 'danger')
        self.assertEqual(dashboard_data[purchase_journal.id]['l10n_es_sii_pending_count'], 3)
        self.assertEqual(dashboard_data[purchase_journal.id]['l10n_es_sii_kanban_state'], 'urgent')
        self.assertEqual(dashboard_data[purchase_journal.id]['l10n_es_sii_state_color'], 'danger')

        sii_document_query_count = [
            query.count('FROM l10n_es_edi_sii_document doc')
            for query in queries
        ]
        self.assertIn(1, sii_document_query_count)
        self.assertTrue(all(count <= 1 for count in sii_document_query_count))
