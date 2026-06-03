# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from unittest.mock import patch

from odoo import Command
from odoo.sql_db import Cursor
from odoo.tests import tagged
from odoo.tests.common import freeze_time
from odoo.tools import SQL

from .common import TestEsEdiCommon

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSiiJournalDashboard(TestEsEdiCommon):

    def _create_journal(self, code, journal_type):
        return self.env['account.journal'].create({
            'name': f'SII Test Journal {code}',
            'type': journal_type,
            'code': code,
            'company_id': self.env.company.id,
        })

    def _create_sale_journal(self, code):
        return self._create_journal(code, 'sale')

    def _create_purchase_journal(self, code):
        return self._create_journal(code, 'purchase')

    def _create_posted_invoice(self, journal, invoice_date):
        invoice = self._create_invoice_es(
            journal_id=journal.id,
            partner_id=self.partner_b.id,
            invoice_date=invoice_date,
            date=invoice_date,
            invoice_line_ids=[{
                'tax_ids': [Command.set(self._get_tax_by_xml_id('s_iva21b').ids)],
            }],
        )
        invoice.action_post()
        return invoice

    def _create_posted_bill(self, journal, partner, invoice_date, taxes=None):
        bill = self._create_invoice_es(
            move_type='in_invoice',
            journal_id=journal.id,
            partner_id=partner.id,
            invoice_date=invoice_date,
            date=invoice_date,
            invoice_line_ids=[{
                'tax_ids': [Command.set(taxes.ids if taxes else [])],
            }],
        )
        bill.action_post()
        return bill

    def _capture_sql(self, callback):
        queries = []
        cursor_execute = Cursor.execute

        def execute(cr, query, params=None, log_exceptions=True):
            if isinstance(query, SQL):
                query, params, _ = query._sql_tuple
            queries.append(cr.mogrify(query, params).decode())
            return cursor_execute(cr, query, params, log_exceptions)

        with patch('odoo.sql_db.Cursor.execute', execute):
            callback()
        return queries

    @freeze_time('2019-01-10 12:00:00')
    def test_sii_dashboard_compute_fields_and_sql(self):
        sale_journal = self._create_sale_journal('SIEJ')
        purchase_journal = self._create_purchase_journal('SIPJ')
        outside_eu_partner = self.env['res.partner'].create({
            'name': 'Outside EU Vendor',
            'country_id': self.env.ref('base.us').id,
        })

        error_invoice = self._create_posted_invoice(sale_journal, '2019-01-10')
        self.env['l10n_es_edi_sii.document'].sudo().create({
            'move_id': error_invoice.id,
            'state': 'to_send',
            'response_message': 'Still failing',
        })

        sent_invoice = self._create_posted_invoice(sale_journal, '2019-01-10')
        self.env['l10n_es_edi_sii.document'].sudo().create({
            'move_id': sent_invoice.id,
            'state': 'accepted',
            'csv': 'CSV-SENT',
            'response_message': 'Correcto',
        })

        latest_csv_invoice = self._create_posted_invoice(sale_journal, '2019-01-10')
        self.env['l10n_es_edi_sii.document'].sudo().create([
            {
                'move_id': latest_csv_invoice.id,
                'state': 'accepted',
                'csv': 'CSV-ACCEPTED',
                'response_message': 'Correcto',
            },
            {
                'move_id': latest_csv_invoice.id,
                'state': 'to_send',
                'csv': 'CSV-LATEST',
                'response_message': 'Retry pending',
            },
        ])

        urgent_invoice = self._create_posted_invoice(sale_journal, '2019-01-01')
        outside_eu_bill_without_taxes = self._create_posted_bill(
            purchase_journal,
            outside_eu_partner,
            '2019-01-10',
        )
        outside_eu_bill_with_taxes = self._create_posted_bill(
            purchase_journal,
            outside_eu_partner,
            '2019-01-10',
            taxes=self._get_tax_by_xml_id('p_iva21_bc'),
        )
        eu_recent_bill_without_taxes = self._create_posted_bill(
            purchase_journal,
            self.partner_a,
            '2019-01-10',
        )
        eu_late_bill_without_taxes = self._create_posted_bill(
            purchase_journal,
            self.partner_a,
            '2019-01-01',
        )
        eu_very_late_bill_without_taxes = self._create_posted_bill(
            purchase_journal,
            self.partner_a,
            '2018-10-01',
        )

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

        def compute_dashboard():
            journals.invalidate_recordset(['l10n_es_sii_pending_count', 'l10n_es_sii_kanban_state'])
            self.assertEqual(sale_journal.l10n_es_sii_pending_count, 3)
            self.assertEqual(sale_journal.l10n_es_sii_kanban_state, 'urgent')
            self.assertEqual(purchase_journal.l10n_es_sii_pending_count, 3)
            self.assertEqual(purchase_journal.l10n_es_sii_kanban_state, 'urgent')

        queries = self._capture_sql(compute_dashboard)
        dashboard_data = journals._get_journal_dashboard_data_batched()
        self.assertEqual(dashboard_data[sale_journal.id]['l10n_es_sii_pending_count'], 3)
        self.assertEqual(dashboard_data[sale_journal.id]['l10n_es_sii_kanban_state'], 'urgent')
        self.assertEqual(dashboard_data[sale_journal.id]['l10n_es_sii_state_color'], 'danger')
        self.assertEqual(dashboard_data[purchase_journal.id]['l10n_es_sii_pending_count'], 3)
        self.assertEqual(dashboard_data[purchase_journal.id]['l10n_es_sii_kanban_state'], 'urgent')
        self.assertEqual(dashboard_data[purchase_journal.id]['l10n_es_sii_state_color'], 'danger')

        dashboard_sql = next(
            query for query in queries
            if 'latest_sii_doc' in query and 'GROUP BY' in query and 'COUNT' in query
        )
        normalized_sql = dashboard_sql.upper()
        self.assertIn('LEFT JOIN LATERAL', normalized_sql)
        self.assertEqual(1, normalized_sql.count('FROM L10N_ES_EDI_SII_DOCUMENT DOC'))
        self.assertNotIn('ACCOUNT_MOVE__L10N_ES_EDI_IS_REQUIRED', normalized_sql)
        self.assertNotIn('ARRAY_AGG', normalized_sql)

        self.env.cr.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {dashboard_sql}")
        explain = '\n'.join(row[0] for row in self.env.cr.fetchall())
        _logger.debug("SII dashboard SQL:\n%s", dashboard_sql)
        _logger.debug("SII dashboard EXPLAIN ANALYZE:\n%s", explain)
