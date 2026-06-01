import requests
from unittest import mock
from urllib.parse import parse_qs

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpPartner(TestL10nFrPdpCommon):

    def test_compute_pdp_identifier(self):
        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '96851575905877',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'company_registry': '96851575905877',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'siret': '968515759',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER 2',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'company_registry': '968515759',
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

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
        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid',
            'pdp_verification_display_state': 'peppol_not_valid',
            'invoice_edi_format': 'ubl_bis3',
        }])

        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('peppol', "0208:0239843188")
        )

        def _request_handler(s: requests.Session, r: requests.PreparedRequest, /, **kwargs):
            self.assertEqual(r.method, "GET")
            origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp']['test']
            self.assertTrue(r.url.startswith(f"{origin}/api/pdp/1/lookup?peppol_identifier="))
            peppol_identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return self._get_peppol_lookup_response(peppol_identifier, "0208:0239843188")
        with (
                mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
                mock.patch.object(requests.sessions.Session, 'send', _request_handler),
        ):
            partner.invoice_edi_format = 'xrechnung'  # this should trigger a verification state update

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid_format',
            'pdp_verification_display_state': 'peppol_not_valid_format',
        }])

    def test_validate_partner_be(self):
        partner = self.partner_b
        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('peppol', "0208:0239843188")
        )
        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid',
            'pdp_verification_display_state': 'peppol_not_valid',
            'invoice_edi_format': 'ubl_bis3',
        }])

        def _request_handler_1(s: requests.Session, r: requests.PreparedRequest, /, **kwargs):
            self.assertEqual(r.method, "GET")
            origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp']['test']
            self.assertTrue(r.url.startswith(f"{origin}/api/pdp/1/lookup?peppol_identifier="))
            peppol_identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return self._get_peppol_lookup_response(peppol_identifier, "0208:0239843188", ubl3_services=False)

        with (
                mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
                mock.patch.object(requests.sessions.Session, 'send', _request_handler_1),
        ):
            partner.button_account_peppol_check_partner_endpoint()

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid_format',
            'pdp_verification_display_state': 'peppol_not_valid_format',
        }])

        def _request_handler_2(s: requests.Session, r: requests.PreparedRequest, /, **kwargs):
            self.assertEqual(r.method, "GET")
            origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp']['test']
            self.assertTrue(r.url.startswith(f"{origin}/api/pdp/1/lookup?peppol_identifier="))
            peppol_identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
            return self._get_peppol_lookup_response(peppol_identifier, "0208:0239843188")

        partner.invoice_sending_method = False
        with (
                mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
                mock.patch.object(requests.sessions.Session, 'send', _request_handler_2),
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
            ('pdp', "0225:968515759_96851575905823")
        )
        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'not_valid',
            'pdp_verification_display_state': 'pdp_not_valid',
            'invoice_edi_format': 'ubl_21_fr',
        }])

        def _request_handler(s: requests.Session, r: requests.PreparedRequest, /, **kwargs):
            self.assertEqual(r.method, "GET")
            origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp']['test']
            if r.url.startswith(f"{origin}/api/pdp/1/annuaire_lookup?pdp_identifier="):
                pdp_identifier = parse_qs(r.path_url.rsplit('?')[1])['pdp_identifier'][0]
                return self._get_annuaire_lookup_response(pdp_identifier, "968515759_96851575905823")
            elif r.url.startswith(f"{origin}/api/pdp/1/lookup?peppol_identifier=0225%3A968515759_96851575905823"):
                peppol_identifier = parse_qs(r.path_url.rsplit('?')[1])['peppol_identifier'][0]
                return self._get_peppol_lookup_response(peppol_identifier, "0225:968515759_96851575905823")

        partner.invoice_sending_method = False
        with (
                mock.patch.object(self.env.registry['res.company'], 'search', lambda *args, **kwargs: self.env.company),
                mock.patch.object(requests.sessions.Session, 'send', _request_handler),
        ):
            partner.button_account_peppol_check_partner_endpoint()

        self.assertRecordValues(partner, [{
            'peppol_verification_state': 'valid',
            'pdp_verification_display_state': 'pdp_valid',
            'invoice_sending_method': False,
        }])
