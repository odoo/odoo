import json
from unittest import mock
from urllib.parse import parse_qs

import requests

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestL10nFrPdpCommon

ANNUAIRE_LINES = [
    {'identifier': '968515759_LIXXBAIL_ASSURANCES', 'platform_id': '0001', 'nature': 'S'},
    {'identifier': '968515759_LIXXBAIL_LOI', 'platform_id': '0002', 'nature': 'S'},
    {'identifier': '968515759', 'platform_id': '0003', 'nature': 'S'},
]


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAnnuaireLookup(TestL10nFrPdpCommon):

    def _annuaire_lines_handler(self, lines, fail=False):
        def handler(session, request, /, **kwargs):
            origin = self.env['account_edi_proxy_client.user']._get_proxy_urls()['pdp']['test']
            if request.url.startswith(f"{origin}/api/pdp/1/pdp_annuaire_lookup"):
                if fail:
                    raise requests.exceptions.ConnectionError('IAP unreachable')
                params = parse_qs(request.path_url.rsplit('?', 1)[1])
                self.assertEqual(params['pdp_endpoint'][0], '968515759')
                self.assertEqual(params['active_only'][0], 'True')
                response = requests.Response()
                response.status_code = 200
                response._content = json.dumps({'annuaire_lines': lines}).encode()
                return response
            return TestL10nFrPdpCommon._request_handler(session, request, **kwargs)
        return handler

    def _open_lookup(self, partner, lines=None, fail=False):
        handler = self._annuaire_lines_handler(ANNUAIRE_LINES if lines is None else lines, fail=fail)
        with mock.patch.object(requests.sessions.Session, 'send', handler):
            action = partner.action_pdp_annuaire_lookup()
        return self.env['l10n_fr_pdp.partner.lookup'].browse(action['res_id'])

    def test_lookup_lists_lines_and_keeps_chosen_identifier(self):
        partner = self.env['res.partner'].create({
            'name': 'Lixxbail',
            'country_id': self.env.ref('base.fr').id,
            'vat': 'FR23334175221',
            'siret': '96851575900034',
            'is_company': True,
        })
        partner.write({
            'peppol_eas': '9957',
            'peppol_endpoint': 'FR23334175221',
            'ubl_cii_format': 'ubl_bis3',
        })
        before = {
            'peppol_eas': partner.peppol_eas,
            'peppol_endpoint': partner.peppol_endpoint,
            'ubl_cii_format': partner.ubl_cii_format,
        }
        wizard = self._open_lookup(partner)
        # Opening the wizard must not guess an identifier (shortest or otherwise).
        self.assertRecordValues(partner, [before])
        self.assertEqual(wizard.partner_id, partner)
        self.assertEqual(wizard.line_count, 3)
        self.assertEqual(
            wizard.available_annuaire_line_ids.mapped('identifier'),
            sorted(line['identifier'] for line in ANNUAIRE_LINES),
        )
        loi = wizard.available_annuaire_line_ids.filtered(
            lambda line: line.identifier == '968515759_LIXXBAIL_LOI',
        )
        self.assertEqual(loi.platform_id, '0002')
        self.assertEqual(loi.nature, 'S')
        wizard.selected_line_id = loi
        wizard.action_change_pdp_endpoint()
        self.assertRecordValues(partner, [{
            'peppol_eas': '0225',
            'peppol_endpoint': '968515759_LIXXBAIL_LOI',
            'ubl_cii_format': 'ubl_21_fr',
        }])

    def test_lookup_siren_from_suffix_endpoint(self):
        partner = self.env['res.partner'].create({
            'name': 'Suffix only',
            'country_id': self.env.ref('base.fr').id,
            'is_company': True,
        })
        partner.write({
            'peppol_eas': '0225',
            'peppol_endpoint': '968515759_LIXXBAIL_LOI',
        })
        self.assertFalse(partner._l10n_fr_pdp_get_siren())
        wizard = self._open_lookup(partner)
        self.assertEqual(wizard.line_count, 3)

    def test_lookup_without_siren_raises(self):
        with self.assertRaises(UserError):
            self.partner_b.action_pdp_annuaire_lookup()

    def test_lookup_without_active_line_raises(self):
        with self.assertRaises(UserError) as error:
            self._open_lookup(self.partner_a, lines=[])
        self.assertIn('No active annuaire line', str(error.exception))

    def test_lookup_unreachable_annuaire_raises(self):
        with self.assertRaises(UserError) as error:
            self._open_lookup(self.partner_a, fail=True)
        self.assertIn('could not be reached', str(error.exception))
