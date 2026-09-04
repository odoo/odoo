from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestPartnerRoutingFields(AccountTestInvoicingCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_routing_scheme_endpoint(self):
        def reset_routing_identifier(partner):
            partner.write({
                'routing_scheme': False,
                'routing_endpoint': False
            })

        partner = self.env['res.partner'].create({
            'name': "A new partner",
            'country_id': self.env.ref('base.nl').id,
            'additional_identifiers': {'DK_CVR': '12345674'},
            'vat': 'NL123456782B90'
        })

        # Base case -> (0184, additional_identifiers)
        self.assertEqual(
            (partner.routing_scheme, partner.routing_endpoint),
            ('0184', partner._get_additional_identifier('DK_CVR')),
        )
        reset_routing_identifier(partner)

        # No EN -> (9944, vat)
        partner.additional_identifiers = False
        self.assertEqual(
            (partner.routing_scheme, partner.routing_endpoint),
            ('9944', partner.vat),
        )
        reset_routing_identifier(partner)

        # No EN nor vat -> (0184, False)
        partner.vat = False
        self.assertEqual(
            (partner.routing_scheme, partner.routing_endpoint),
            (False, False),
        )

        # Create a partner, fill the peppol fields, then set the country
        partner_1 = self.env['res.partner'].create({
            'name': "A new partner",
            'vat': 'BA12345674',
            'routing_scheme': '9924',
            'routing_endpoint': 'BA12345674'
        })
        partner_1.country_id = self.env.ref('base.ba').id
        self.assertEqual(
            (partner_1.routing_scheme, partner_1.routing_endpoint),
            ('9924', 'BA12345674'),
        )

        # Create a partner, set the country, then fill the peppol fields
        partner_2 = self.env['res.partner'].create({
            'name': "A new partner",
            'country_id': self.env.ref('base.ba').id,
        })
        partner_2.write({
            'vat': 'BA12345674',
            'routing_scheme': '9924',
            'routing_endpoint': 'BA12345674',
        })
        self.assertEqual(
            (partner_2.routing_scheme, partner_2.routing_endpoint),
            ('9924', 'BA12345674'),
        )

        # Change the country, the value is not changed since there is no better value so far
        partner_2.country_id = self.env.ref('base.be')
        self.assertEqual(
            (partner_2.routing_scheme, partner_2.routing_endpoint),
            ('9924', 'BA12345674'),
        )
        # Change the country and add a new additional identifier, endpoint is recomputed
        partner_2.additional_identifiers = {'BE_EN': '0477.472.701'}
        self.assertEqual(
            (partner_2.routing_scheme, partner_2.routing_endpoint),
            ('0208', '0477472701'),
        )

    def test_partner_ubl_cii_formats(self):
        def _get_ubl_cii_formats_info(self):
            return {
                'ubl_no_country': {
                    'on_peppol': True,
                    'countries': False,
                },
                'peppol': {
                    'on_peppol': True,
                    'countries': ['NZ', 'AU'],
                },
                'cii': {
                    'sequence': 90,
                    'on_peppol': False,
                    'countries': ['AU'],
                },
            }

        Partner = self.env['res.partner']
        partner_nz = self.env['res.partner'].create({
            'name': "NZ partner",
            'country_id': self.env.ref('base.nz').id,
        })
        partner_be = self.env['res.partner'].create({
            'name': "BE partner",
            'country_id': self.env.ref('base.be').id,
        })
        partner_au = self.env['res.partner'].create({
            'name': "AU partner",
            'country_id': self.env.ref('base.au').id,
        })
        with patch.object(self.env.registry['res.partner'], '_get_ubl_cii_formats_info', _get_ubl_cii_formats_info):
            self.assertEqual(Partner._get_ubl_cii_formats(), ['ubl_no_country', 'peppol', 'cii'])
            self.assertEqual(Partner._get_ubl_cii_formats_by_country()['NZ'], ['peppol'])
            self.assertEqual(Partner._get_ubl_cii_formats_by_country()['AU'], ['peppol', 'cii'])
            self.assertEqual(Partner._get_peppol_formats(), ['ubl_no_country', 'peppol'])
            self.assertEqual(partner_au._get_suggested_ubl_cii_edi_format(), 'cii')  # AU matches 2 formats but 'cii' has a lower sequence
            self.assertEqual(partner_nz._get_suggested_ubl_cii_edi_format(), 'peppol')
            self.assertFalse(partner_be._get_suggested_ubl_cii_edi_format())

    def test_routing_endpoint_sanitized_be_additional_identifiers(self):
        partner = self.env['res.partner'].create({
            'name': "BE partner dots",
            'country_id': self.env.ref('base.be').id,
            'additional_identifiers': {'BE_EN': '0477.472.701'},
            'vat': False
        })
        self.assertEqual(partner.routing_scheme, '0208')
        self.assertEqual(partner.routing_endpoint, '0477472701')

    def test_validate_fr_vat_routing_identifier(self):
        """ A France VAT (EAS 9957) used as routing scheme/endpoint is validated as a VAT:
        a valid number is accepted and normalized, an invalid one raises a clear error.
        """
        partner = self.env['res.partner'].create({'name': "FR VAT Routing"})

        # A valid France VAT is accepted as the routing endpoint.
        partner.routing_identifier = '9957:FR23334175221'
        self.assertRecordValues(partner, [{
            'routing_scheme': '9957',
            'routing_endpoint': 'FR23334175221',
        }])

        # An invalid France VAT is rejected with a VAT validation error.
        with self.assertRaisesRegex(ValidationError, "for partner does not seem to be valid"):
            partner.routing_identifier = '9957:FR00000000000'

    def test_routing_identifier_override(self):
        """ Test that the routing identifier override updates the routing scheme and endpoint
        and falls back to the default behavior when the routing identifier override is cleared.
        """
        partner = self.env['res.partner'].create({
            'name': "Route Partner",
            'country_id': self.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })
        original_identifier = partner.routing_identifier

        # Without routing_identifier_override, the routing_identifier is computed from the VAT.
        self.assertTrue(partner.routing_identifier)

        # 1. Setting the routing_identifier_override updates the routing scheme, endpoint and identifier.
        partner.routing_identifier_override = '9925:BE0505665156'
        self.assertEqual(
            (partner.routing_scheme, partner.routing_endpoint, partner.routing_identifier),
            ('9925', 'BE0505665156', '9925:BE0505665156')
        )

        # 2. Changing the routing scheme and endpoint updates the routing_identifier_override.
        partner.write({'routing_scheme': '0208', 'routing_endpoint': '0477472701'})
        self.assertEqual(partner.routing_identifier_override, '0208:0477472701')

        # Clearing the routing_identifier_override computes the routing identifier from the VAT.
        partner.routing_identifier_override = False
        self.assertEqual(partner.routing_identifier, original_identifier)

    def test_clear_vat_and_additional_identifiers_clears_routing_fields(self):
        """ Test that clearing VAT and additional identifiers also clears the routing fields when
        routing_identifier_override is not set, but keeps the routing fields when routing_identifier_override is set.
        """
        partner_1 = self.env['res.partner'].create({
            'name': "Route Partner 1",
            'country_id': self.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })
        partner_2 = partner_1.copy({'name': "Route Partner 2"})

        self.assertEqual(partner_1.routing_identifier, '0208:0477472701')

        # Removing VAT and additional_identifiers clears scheme, endpoint
        partner_1.write({'vat': False, 'additional_identifiers': False})
        self.assertFalse(partner_1.routing_scheme)
        self.assertFalse(partner_1.routing_endpoint)

        # Clearing VAT and additional identifiers does not clear the routing fields as routing_identifier_override is set.
        partner_2.routing_identifier_override = '9925:BE0505665156'
        partner_2.write({'vat': False, 'additional_identifiers': False})
        self.assertEqual(
            (partner_2.routing_scheme, partner_2.routing_endpoint),
            ('9925', 'BE0505665156')
        )

        # Clearing the override on a partner with no VAT/additional_identifiers clears scheme, endpoint
        partner_2.routing_identifier_override = False
        self.assertFalse(partner_2.routing_scheme)
        self.assertFalse(partner_2.routing_endpoint)
