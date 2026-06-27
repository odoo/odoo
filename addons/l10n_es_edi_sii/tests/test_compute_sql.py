# Part of Odoo. See LICENSE file for full copyright and licensing details.
"""Tests that auto-derived compute_sql makes l10n_es_edi_sii fields searchable.

The fields ``l10n_es_edi_is_required`` and ``l10n_es_edi_sii_state`` on
``account.move`` have no explicit ``search`` method or ``compute_sql``.
The ORM should have auto-derived SQL for them at field-setup time, making
them transparently searchable and sortable.
"""

import logging

from odoo.addons.l10n_es_edi_sii.tests.common import TestEsEdiCommon


_logger = logging.getLogger(__name__)


class TestComputeSQL(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A qualifying Spanish invoice with SII tax agency configured
        cls.invoice_es = cls._create_invoice_es(
            invoice_line_ids=[{'tax_ids': [cls._get_tax_by_xml_id('s_iva21b').id]}],
        )
        cls.invoice_es.action_post()

        # A non-qualifying vendor bill with no SII-relevant taxes.
        cls.invoice_non_es = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'ref': 'NO-SII',
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 500.0,
                'tax_ids': [(5, 0, 0)],
            })],
        })
        cls.invoice_non_es.action_post()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _assert_searchable(self, field_name):
        field = self.env['account.move']._fields[field_name]
        self.assertTrue(
            field._description_searchable,
            f"Field {field_name!r} should be searchable via auto-derived compute_sql",
        )

    def _search(self, domain):
        return self.env['account.move'].search(domain)

    def _query_sql(self, domain, order=None):
        sql = self.env['account.move']._search(domain, order=order).select()
        code, params, _to_flush = sql._sql_tuple
        return self.env.cr.mogrify(code, params).decode()

    # ── l10n_es_edi_is_required ───────────────────────────────────────────────

    def test_is_required_field_is_searchable(self):
        self._assert_searchable('l10n_es_edi_is_required')

    def test_search_is_required_true(self):
        results = self._search([('l10n_es_edi_is_required', '=', True)])
        self.assertIn(self.invoice_es, results)
        self.assertNotIn(self.invoice_non_es, results)

    def test_search_is_required_false(self):
        results = self._search([('l10n_es_edi_is_required', '=', False)])
        self.assertNotIn(self.invoice_es, results)
        self.assertIn(self.invoice_non_es, results)

    def test_order_by_is_required(self):
        """Sorting by a non-stored compute_sql field should not crash."""
        moves = self.env['account.move'].search(
            [('id', 'in', (self.invoice_es | self.invoice_non_es).ids)],
            order='l10n_es_edi_is_required desc',
        )
        self.assertEqual(moves[0], self.invoice_es)

    # ── l10n_es_edi_sii_state ─────────────────────────────────────────────────

    def test_sii_state_field_is_searchable(self):
        self._assert_searchable('l10n_es_edi_sii_state')

    def test_sii_state_search_query_contains_compute_sql(self):
        """Show the SQL emitted for a search on the auto-derived compute_sql."""
        query_sql = self._query_sql([('l10n_es_edi_sii_state', '=', 'to_send')])
        _logger.info(
            "SQL for account.move search on l10n_es_edi_sii_state:\n%s",
            query_sql,
        )

        self.assertIn('CASE WHEN', query_sql, query_sql)
        self.assertIn('"l10n_es_edi_sii_document"', query_sql, query_sql)
        self.assertIn("'accepted_with_errors'", query_sql, query_sql)
        self.assertIn("'to_send'", query_sql, query_sql)

    def test_search_sii_state_to_send(self):
        """A qualifying invoice with no SII document should show up as 'to_send'."""
        results = self._search([('l10n_es_edi_sii_state', '=', 'to_send')])
        self.assertIn(self.invoice_es, results)

    def test_search_sii_state_false(self):
        """A non-qualifying invoice has no state (False/NULL)."""
        results = self._search([('l10n_es_edi_sii_state', '=', False)])
        self.assertIn(self.invoice_non_es, results)
        self.assertNotIn(self.invoice_es, results)

    def test_search_sii_state_sent(self):
        """After a successful SII document is created, state should be 'sent'."""
        doc = self.env['l10n_es_edi_sii.document'].sudo().create({
            'move_id': self.invoice_es.id,
            'state': 'accepted',
        })
        results = self._search([('l10n_es_edi_sii_state', '=', 'sent')])
        self.assertIn(self.invoice_es, results)
        doc.unlink()

    def test_order_by_sii_state(self):
        results = self.env['account.move'].search(
            [('id', 'in', (self.invoice_es | self.invoice_non_es).ids)],
            order='l10n_es_edi_sii_state asc',
        )
        self.assertEqual(len(results), 2)
