# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_get_siren_from_vat(self):
        for vat, expected_siren in (
            ('FR23334175221', '334175221'),
            ('fr 23 334 175 221', '334175221'),
            ('BE23334175221', None),
        ):
            with self.subTest(vat=vat):
                partner = self.env['res.partner'].new({'vat': vat})
                self.assertEqual(partner._l10n_fr_get_siren_from_vat(), expected_siren)

    def test_autocomplete_registration_number(self):
        """The name and identifier widgets search SIREN/SIRET in France, not the origin country."""
        for field_name, query, identifier in (
            ('name', '005520325', '005520325'),
            ('name', '005 520 325 00019', '00552032500019'),
            ('fr_siren', '005520325', '005520325'),
            ('fr_siret', '00552032500019', '00552032500019'),
        ):
            with self.subTest(field_name=field_name, query=query), patch.object(
                self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', return_value=({'data': []}, False),
            ) as request:
                self.env['res.partner'].autocomplete_by_field(field_name, query, self.env.ref('base.be').id, timeout=8, include_branches=True)
                request.assert_called_once_with('search_by_vat', {
                    'query': identifier,
                    'query_country_code': 'FR',
                    'include_branches': True,
                    'supported_enrichment_types': ['duns', 'vat'],
                }, timeout=8)

    def test_autocomplete_name(self):
        """Name searches advertise identifier enrichment while keeping the chosen country."""
        with patch.object(
            self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', return_value=({'data': []}, False),
        ) as request:
            self.env['res.partner'].autocomplete_by_field('name', 'riquier', self.env.ref('base.fr').id, include_branches=True)
        request.assert_called_once_with('search_by_name', {
            'query': 'riquier',
            'query_country_code': 'FR',
            'include_branches': True,
            'supported_enrichment_types': ['duns', 'vat'],
        }, timeout=15)

    def test_autocomplete_freshness_warning(self):
        """Old or unavailable INPI complements warn without losing usable Sirene values."""
        for status, warning in (
            (None, False),  # An older IAP server does not return freshness metadata.
            ({'inpi_stale': False, 'inpi_last_sync': '2026-11-09 10:00:00'}, False),
            ({'inpi_stale': True, 'inpi_last_sync': '2026-01-01 10:00:00'}, True),
            ({'inpi_stale': True, 'inpi_last_sync': False}, True),
        ):
            with self.subTest(status=status):
                result = self.env['res.partner']._process_enriched_response({
                    'data': {'name': 'Test company', 'additional_identifiers': {'FR_SIRET': '00552032500019'}},
                    'enrichment_status': status,
                }, False)
                self.assertEqual(result['name'], 'Test company')
                self.assertEqual(result['additional_identifiers']['FR_SIRET'], '00552032500019')
                self.assertEqual(bool(result.get('warning')), warning)
                self.assertNotIn('enrichment_status', result)
