# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon


class TestResPartner(BaseCommon):

    def test_enrich_selected_country(self):
        """Selection, including a foreign DUNS, supplies the country and supported formats."""
        for country_code in ('FR', 'BE'):
            country = self.env.ref(f'base.{country_code.lower()}')
            partner = self.env['res.partner'].with_context(enriched_company_data={'country_id': {'id': country.id}})
            for enrichment_type, identifier in (('duns', '123456789'), ('vat', 'FR00552032500019')):
                with self.subTest(country=country_code, enrichment_type=enrichment_type), patch.object(
                    self.env.registry['iap.autocomplete.api'], '_request_partner_autocomplete', return_value=({'data': {}}, False),
                ) as request:
                    if enrichment_type == 'duns':
                        partner.enrich_by_duns(identifier)
                    else:
                        partner.enrich_by_vat(identifier)
                    request.assert_called_once_with(f'enrich_by_{enrichment_type}', {
                        enrichment_type: identifier,
                        'query_country_code': country_code,
                        'supported_enrichment_types': partner._get_supported_enrichment_types(),
                    }, timeout=15)

    def test_enrich_without_selected_country(self):
        """An unknown target country must not be replaced by the database's own country."""
        partner = self.env['res.partner']
        self.assertFalse(partner._get_enrichment_request_params()['query_country_code'])
        partner = partner.new({'country_id': self.env.ref('base.be').id})
        self.assertEqual(partner._get_enrichment_request_params()['query_country_code'], 'BE')

    def test_enrichment_response(self):
        """Keep existing model values, without inventing a VAT from an opaque query key."""
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
        self.assertNotIn('vat', result)
        self.assertFalse(result.get('warning'))
        self.assertEqual(request.call_args.args[0], 'enrich_by_vat')
