import requests
from unittest import mock
from urllib.parse import parse_qs

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.mail.tests.common import MailCase

from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import CPRO_INVOICE_IDENTIFIER

from .common import TestL10nFrPdpCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nFrPdpPartner(TestL10nFrPdpCommon, MailCase):

    def test_compute_pdp_identifier(self):
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
            'company_registry': '968515759',
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

        partner_siret = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER SIRET',
            'street': 'Rue Fabricy, 16',
            'zip': '59000',
            'city': 'Lille',
            'country_id': self.env.ref('base.fr').id,
            'phone': '+33 1 23 45 67 89',
            'vat': 'FR23334175221',
            'additional_identifiers': {'FR_SIRET': '96851575905808'},
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner_siret, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner_siren = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER SIREN',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'additional_identifiers': {'FR_SIREN': '968515759'},
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner_siren, [{
            'peppol_endpoint': '968515759',
            'peppol_eas': '0225',
        }])

        partner_ctc = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER CTC',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'additional_identifiers': {'FR_CTC': '968515759_96851575905808'},
            'invoice_edi_format': 'ubl_21_fr',
        })
        self.assertRecordValues(partner_ctc, [{
            'peppol_endpoint': '968515759_96851575905808',
            'peppol_eas': '0225',
        }])

        partner_vat = self.env["res.partner"].create({
            'name': 'SUPER FRENCH PARTNER CTC',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'invoice_edi_format': 'ubl_21_fr',
            'peppol_endpoint': 'FR23334175221',
            'peppol_eas': '9957',
        })
        self.assertRecordValues(partner_vat, [{
            'peppol_endpoint': 'FR23334175221',
            'peppol_eas': '9957',
        }])
        partner_vat.additional_identifiers = {'FR_SIREN': '968515759'}
        self.assertRecordValues(partner_vat, [{
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
        partner.button_account_peppol_check_partner_endpoint()
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
            ('peppol', "0208:0239843188")
        )
        partner.button_account_peppol_check_partner_endpoint()
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
        partner.button_account_peppol_check_partner_endpoint()
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

    def test_track_pdp_verification_display_state(self):
        partner = self.partner_a
        messages_before = partner.message_ids

        partner.button_account_peppol_check_partner_endpoint()
        self.env.cr.precommit.run()

        message = partner.message_ids - messages_before
        self.assertEqual(len(message), 1)
        self.assertMessageFields(message, {
            'tracking_values': [(
                'pdp_verification_display_state',
                'selection',
                'Not verified yet',
                'Partner is not in the annuaire',
            )],
        })

    def test_track_peppol_verification_state_for_non_pdp_company(self):
        company = self.env['res.company'].create({'name': 'Belgian Company'})
        partner = self.partner_a.with_company(company)
        messages_before = partner.message_ids

        partner._log_verification_state_update('not_verified', 'not_valid')
        self.env.cr.precommit.run()

        message = partner.message_ids - messages_before
        self.assertEqual(len(message), 1)
        self.assertMessageFields(message, {
            'tracking_values': [(
                'peppol_verification_state',
                'selection',
                'Unchecked',
                'Partner is not on Peppol',
            )],
        })

    def test_validate_partner_fr_b2g(self):
        partner = self.partner_a
        self.assertEqual(
            partner._get_pdp_receiver_identification_info(),
            ('pdp', "0225:968515759_96851575905823")
        )
        partner.button_account_peppol_check_partner_endpoint()
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
                return self._get_annuaire_lookup_response(pdp_identifier, "968515759_96851575905823", b2g=True)
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
            'peppol_supported_documents': [CPRO_INVOICE_IDENTIFIER],
        }])
        self.assertTrue(self.env['account.edi.xml.ubl_21_fr']._pdp_is_b2g(partner))
