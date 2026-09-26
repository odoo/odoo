# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import Mock, patch

from odoo.tests import TransactionCase


class TestResPartner(TransactionCase):
    def test_search_french_registration_number(self):
        """SIREN and SIRET searches must target France, including from the name field."""
        searches = (
            ('name', '005520325'),
            ('FR_SIREN', '005520325'),
            ('FR_SIRET', '00552032500019'),
        )
        with (
            patch.object(self.env.registry['ir.module.module'], '_get', return_value=Mock(state='installed')),
            patch.object(
                self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete',
                return_value=({'data': []}, False),
            ) as request,
        ):
            for field_name, identifier in searches:
                with self.subTest(field_name=field_name):
                    self.env['res.partner'].autocomplete_by_field(field_name, identifier, False)
                    request.assert_called_once_with('search_by_vat', {
                        'query': identifier,
                        'query_country_code': 'FR',
                        'supported_enrichment_types': ['duns', 'vat'],
                    }, timeout=15)
                    request.reset_mock()

    def test_search_by_name_supports_inpi(self):
        """Name searches tell IAP that this client can consume INPI results."""
        with (
            patch.object(self.env.registry['ir.module.module'], '_get', return_value=Mock(state='installed')),
            patch.object(
                self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete',
                return_value=({'data': []}, False),
            ) as request,
        ):
            self.env['res.partner'].autocomplete_by_name('riquier', self.env.ref('base.fr').id)

        request.assert_called_once_with('search_by_name', {
            'query': 'riquier',
            'query_country_code': 'FR',
            'supported_enrichment_types': ['duns', 'vat'],
        }, timeout=15)

    def test_search_without_french_localization(self):
        """Do not advertise INPI support when the French localization is not installed."""
        with (
            patch.object(self.env.registry['ir.module.module'], '_get', return_value=Mock(state='uninstalled')),
            patch.object(
                self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete',
                return_value=({'data': []}, False),
            ) as request,
        ):
            self.env['res.partner'].autocomplete_by_name('riquier', self.env.ref('base.fr').id)
            request.assert_called_once_with('search_by_name', {
                'query': 'riquier',
                'query_country_code': 'FR',
                'supported_enrichment_types': ['duns'],
            }, timeout=15)

            request.reset_mock()
            self.env['res.partner'].autocomplete_by_field(
                'FR_SIREN', '005520325', self.env.ref('base.be').id,
            )
            request.assert_called_once_with('search_by_vat', {
                'query': '005520325',
                'query_country_code': 'BE',
                'supported_enrichment_types': ['duns'],
            }, timeout=15)

    def test_enrich_by_vat(self):
        """INPI fields supported by existing Odoo models must be kept in the response."""
        response = {'data': {
            'name': 'ETABLISSEMENTS ADRIEN RIQUIER',
            'country_code': 'FR',
            'ape': '4674B',
            'additional_identifiers': {
                'FR_SIREN': '005520325',
                'FR_SIRET': '00552032500019',
            },
        }}
        with patch.object(
            self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', return_value=(response, False),
        ) as request:
            result = self.env['res.partner'].enrich_by_vat('005520325')

        self.assertEqual(result['name'], 'ETABLISSEMENTS ADRIEN RIQUIER')
        self.assertEqual(result['country_id']['id'], self.env.ref('base.fr').id)
        self.assertEqual(result['ape'], '4674B')
        self.assertEqual(result['additional_identifiers'], {
            'FR_SIREN': '005520325',
            'FR_SIRET': '00552032500019',
        })
        request.assert_called_once_with('enrich_by_vat', {'vat': '005520325'}, timeout=15)
