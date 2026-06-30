from unittest import mock

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon, mock_pdp_annuaire_lookup, mock_pdp_lookup_not_found, mock_pdp_lookup_success


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpPartner(TestL10nFrPdpCommon):

    def test_pdp_identifier_derivation(self):
        # `routing_identifier` is no longer auto-computed from the registry: the PDP routing endpoint
        # is set explicitly, while the SIREN is derived from the FR SIRET/SIREN identifier.
        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'additional_identifiers': {'FR_SIRET': '96851575905808'},
            'invoice_edi_format': 'ubl_21_fr',
        })
        # SIREN derived from the SIRET; no routing endpoint is auto-filled.
        self.assertEqual(partner._l10n_fr_pdp_get_siren(), '968515759')
        self.assertFalse(partner.routing_identifier)

        # Setting the endpoint explicitly routes the partner via PDP (EAS 0225).
        partner.routing_identifier = '0225:968515759_96851575905808'
        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('pdp', '0225:968515759_96851575905808'),
        )

        # A partner identified by SIREN only (9 digits) derives the same SIREN.
        partner_siren = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'additional_identifiers': {'FR_SIREN': '968515759'},
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertEqual(partner_siren._l10n_fr_pdp_get_siren(), '968515759')

    def test_pdp_edi_formats(self):
        partner = self.partner_a
        partner.invoice_sending_method = 'peppol'
        self.assertEqual(partner._get_pdp_receiver_identification_info()[0], 'pdp')
        with self.assertRaises(UserError):
            partner.invoice_edi_format = 'ubl_bis3'

        partner.invoice_sending_method = 'email'
        partner.invoice_edi_format = 'ubl_bis3'

    def test_validate_partner_be_invalid_format(self):
        partner = self.partner_b
        with mock_pdp_lookup_not_found(['0208:0239843188']):  # not on Peppol
            partner.button_account_peppol_check_partner_endpoint()
        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid',
            'pdp_verification_display_state': 'peppol_not_valid',
            'invoice_edi_format': 'ubl_bis3',
        }])

        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('peppol', '0208:0239843188')
        )

        with (
            mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
            mock_pdp_lookup_success(['0208:0239843188']),
        ):
            partner.invoice_edi_format = 'xrechnung'
            partner.button_account_peppol_check_partner_endpoint()

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid_format',
            'pdp_verification_display_state': 'peppol_not_valid_format',
        }])

    def test_validate_partner_be(self):
        partner = self.partner_b
        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('peppol', '0208:0239843188')
        )
        with mock_pdp_lookup_not_found(['0208:0239843188']):  # not on Peppol
            partner.button_account_peppol_check_partner_endpoint()
        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid',
            'pdp_verification_display_state': 'peppol_not_valid',
            'invoice_edi_format': 'ubl_bis3',
        }])

        with (
            mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
            mock_pdp_lookup_success(['0208:0239843188'], ubl_services=False),
        ):
            partner.button_account_peppol_check_partner_endpoint()

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid_format',
            'pdp_verification_display_state': 'peppol_not_valid_format',
        }])

        partner.invoice_sending_method = False
        with (
            mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
            mock_pdp_lookup_success(['0208:0239843188']),
        ):
            partner.button_account_peppol_check_partner_endpoint()

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'valid',
            'pdp_verification_display_state': 'peppol_valid',
            'invoice_sending_method': False,
        }])

    def test_validate_partner_fr(self):
        partner = self.partner_a
        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('pdp', "0225:968515759_96851575905808")
        )
        with mock_pdp_annuaire_lookup():  # not in the annuaire
            partner.button_account_peppol_check_partner_endpoint()
        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid',
            'pdp_verification_display_state': 'pdp_not_valid',
            'invoice_edi_format': 'ubl_21_fr',
        }])

        partner.invoice_sending_method = False
        with (
            mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
            mock_pdp_annuaire_lookup('968515759_96851575905808'),
            mock_pdp_lookup_success(['0225:968515759_96851575905808']),
        ):
            partner.button_account_peppol_check_partner_endpoint()

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'valid',
            'pdp_verification_display_state': 'pdp_valid',
            'invoice_sending_method': False,
        }])
