from unittest.mock import Mock, patch

from odoo.tests import TransactionCase


class TestResPartner(TransactionCase):
    def test_search_french_registration_number_from_name(self):
        with (
            patch.object(self.env.registry['ir.module.module'], '_get', return_value=Mock(state='installed')),
            patch.object(
                self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete',
                return_value=({'data': []}, False),
            ) as request,
        ):
            self.env['res.partner'].autocomplete_by_field('name', '005520325', False)

        request.assert_called_once_with('search_by_vat', {
            'query': '005520325',
            'query_country_code': 'FR',
            'supported_enrichment_types': ['duns', 'vat'],
        }, timeout=15)

    def test_enrich_by_vat(self):
        response = {'data': {'name': 'ETABLISSEMENTS ADRIEN RIQUIER'}}
        with patch.object(
            self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', return_value=(response, False),
        ) as request:
            result = self.env['res.partner'].enrich_by_vat('005520325')

        self.assertEqual(result['name'], 'ETABLISSEMENTS ADRIEN RIQUIER')
        request.assert_called_once_with('enrich_by_vat', {'vat': '005520325'}, timeout=15)
