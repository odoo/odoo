import re
from base64 import b64encode
from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import file_open

from odoo.addons.l10n_fr_pdp.tests.common import FAKE_UUID, FILE_PATH
from odoo.addons.l10n_fr_pdp.tests.messages_common import TestPdpMessagesCommon
from odoo.addons.l10n_fr_pdp.utils import transport_parties as parties

MESSAGE_UUID = FAKE_UUID[1]


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPdpTransportAlert(TestPdpMessagesCommon):

    sender = '0184:16356706'
    receiver = '0088:5798009811512'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        document = b64encode(file_open(f'{FILE_PATH}/document', mode='rb').read())
        enc_key = file_open(f'{FILE_PATH}/enc_key', mode='rb').read()
        decrypted = cls.proxy_user._decrypt_data(document, enc_key)
        # Drop the invoice period so the import does not depend on optional line dates.
        cls.original_xml = re.sub(rb'<cac:InvoicePeriod>.*?</cac:InvoicePeriod>', b'', decrypted, flags=re.S)
        # Same document, but the seller legal identity is the French SIREN 991192543.
        cls.french_seller_xml = cls.original_xml.replace(b'DK16356706', b'991192543')
        assert cls.original_xml != cls.french_seller_xml

    @classmethod
    def _get_mock_data(cls, error=False, nr_invoices=1):
        proxy_documents, responses = super()._get_mock_data(error=error, nr_invoices=nr_invoices)
        for message in responses['/api/pdp/1/get_all_documents']['result'].get('messages') or []:
            message['sender'] = cls.sender
            message['receiver'] = cls.receiver
        return proxy_documents, responses

    def _alert_bodies(self, move):
        return [
            body for body in move.message_ids.mapped('body')
            if body and 'Peppol transport alert' in body
        ]

    def _receive(self, xml_content, sender):
        type(self).sender = sender
        model = type(self.env['account_edi_proxy_client.user'])
        with patch.object(model, '_peppol_get_decoded_document', return_value=xml_content):
            self.env['account_edi_proxy_client.user']._cron_peppol_get_new_documents()
        return self.env['account.move'].search([('peppol_message_uuid', '=', MESSAGE_UUID)])


    def _create_flagged_move(self, xml_content=None, sender='0225:931473060', **kwargs):
        """Draft vendor bill carrying the transport envelope, without the proxy fetch."""
        vendor = self.env['res.partner'].create({
            'name': 'SubscriptionSeller',
            'country_id': self.env.ref('base.fr').id,
        })
        tax = self.env['account.chart.template'].ref('tva_acq_normale')
        move = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': vendor.id,
            'invoice_date': '2024-12-01',
            'invoice_line_ids': [Command.create({
                'name': 'Service',
                'quantity': 1,
                'price_unit': 100.0,
                'account_id': self.company_data['default_account_expense'].id,
                'tax_ids': [Command.set(tax.ids)],
            })],
            **kwargs,
        })
        self.env['ir.attachment'].create({
            'name': 'incoming.xml',
            'raw': xml_content or self.french_seller_xml,
            'mimetype': 'application/xml',
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move._l10n_fr_pdp_transport_apply({'sender': sender, 'receiver': self.receiver})
        return move

    def test_extract_siren(self):
        self.assertEqual(parties.extract_siren('0225', '968515759_96851575905823'), '968515759')
        self.assertEqual(parties.extract_siren('0225', '931473060'), '931473060')
        self.assertEqual(parties.extract_siren('0009', '96851575905823'), '968515759')
        self.assertEqual(parties.extract_siren('', 'FR 23 334175221'), '334175221')
        self.assertEqual(parties.extract_siren('0184', '16356706'), None)
        self.assertEqual(parties.extract_siren('0225', 'LIXXBAIL'), None)

    def test_compute_alert(self):
        sender = '0225:931473060'
        legal = [['0002', '931473060'], ['', 'FR12931473060']]
        other = [['0002', '991192543']]
        cases = [
            # (sender, tokens, mandate, expected)
            ('', other, False, (parties.LEVEL_NONE, False)),
            (sender, legal, False, (parties.LEVEL_NONE, False)),
            ('0225:931473060_93147306000012', legal, False, (parties.LEVEL_NONE, False)),
            (sender, other, True, (parties.LEVEL_NONE, False)),
            (sender, other, False, (parties.LEVEL_CRITICAL, parties.REASON_SIREN_MISMATCH)),
            (sender, [], False, (parties.LEVEL_WARNING, parties.REASON_MISSING_PARTIES)),
            (sender, [['GLN', 'TBCNTRL00002']], False, (parties.LEVEL_WARNING, parties.REASON_UNCOMPARABLE)),
            ('0184:16356706', [['DK:SE', 'DK16356706']], False, (parties.LEVEL_NONE, False)),
            # A crafted party carrying the victim and the sender identities must not pass silently.
            (sender, legal + other, False, (parties.LEVEL_WARNING, parties.REASON_AMBIGUOUS)),
        ]
        for sender_id, tokens, mandate, expected in cases:
            with self.subTest(sender=sender_id, tokens=tokens, mandate=mandate):
                self.assertEqual(parties.compute_alert(sender_id, tokens, mandate), expected)

    def test_parse_ubl_ignores_endpoint(self):
        xml_tree = etree.fromstring(b'''<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:InvoiceTypeCode>389</cbc:InvoiceTypeCode>
          <cac:AccountingSupplierParty><cac:Party>
            <cbc:EndpointID schemeID="0225">931473060</cbc:EndpointID>
            <cac:PartyLegalEntity><cbc:CompanyID schemeID="0002">991192543</cbc:CompanyID></cac:PartyLegalEntity>
          </cac:Party></cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty><cac:Party>
            <cac:PartyIdentification><cbc:ID schemeID="0009">96851575905899</cbc:ID></cac:PartyIdentification>
          </cac:Party></cac:AccountingCustomerParty>
        </Invoice>''')
        result = parties.parse_parties(xml_tree)
        self.assertEqual(result['type_code'], '389')
        self.assertEqual(result['seller'], [['0002', '991192543']])
        self.assertEqual(result['buyer'], [['0009', '96851575905899']])

    def test_parse_cii(self):
        xml_tree = etree.fromstring(b'''<rsm:CrossIndustryInvoice
            xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"
            xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100">
          <rsm:ExchangedDocument><ram:TypeCode>380</ram:TypeCode></rsm:ExchangedDocument>
          <rsm:SupplyChainTradeTransaction><ram:ApplicableHeaderTradeAgreement>
            <ram:SellerTradeParty>
              <ram:SpecifiedLegalOrganization><ram:ID schemeID="0002">931473060</ram:ID></ram:SpecifiedLegalOrganization>
              <ram:SpecifiedTaxRegistration><ram:ID schemeID="VA">FR12931473060</ram:ID></ram:SpecifiedTaxRegistration>
            </ram:SellerTradeParty>
            <ram:BuyerTradeParty><ram:ID>BUYER</ram:ID></ram:BuyerTradeParty>
          </ram:ApplicableHeaderTradeAgreement></rsm:SupplyChainTradeTransaction>
        </rsm:CrossIndustryInvoice>''')
        result = parties.parse_parties(xml_tree)
        self.assertEqual(result['type_code'], '380')
        self.assertEqual(result['seller'], [['0002', '931473060'], ['VA', 'FR12931473060']])
        self.assertEqual(result['buyer'], [['', 'BUYER']])

    def test_matching_sender_is_silent(self):
        move = self._receive(self.original_xml, '0184:16356706')
        self.assertTrue(move)
        self.assertFalse(move.to_check)
        self.assertEqual(move.state, 'draft')
        self.assertFalse(self._alert_bodies(move))

    def test_empty_sender_is_silent(self):
        move = self._receive(self.original_xml, '')
        self.assertTrue(move)
        self.assertFalse(move.to_check)
        self.assertFalse(self._alert_bodies(move))

    def test_same_siren_is_silent(self):
        move = self._receive(self.french_seller_xml, '0225:991192543_99119254300012')
        self.assertTrue(move)
        self.assertFalse(move.to_check)
        self.assertFalse(self._alert_bodies(move))

    def test_sender_not_comparable_is_warning(self):
        move = self._receive(self.original_xml, '0225:931473060')
        self.assertTrue(move.to_check)
        self.assertEqual(move.state, 'draft')
        self.assertIn('cannot be compared', self._alert_bodies(move)[0])

    def test_sender_mismatch_is_critical(self):
        move = self._receive(self.french_seller_xml, '0225:931473060')
        self.assertTrue(move.to_check)
        self.assertEqual(move.state, 'draft')
        body = self._alert_bodies(move)[0]
        self.assertIn('931473060', body)
        self.assertIn('991192543', body)
        self.assertIn('Peppol transport alert', body)

    def test_self_billing_compares_the_buyer(self):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
        })
        xml = b'''<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
            xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
            xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
          <cbc:InvoiceTypeCode>389</cbc:InvoiceTypeCode>
          <cac:AccountingSupplierParty><cac:Party>
            <cac:PartyLegalEntity><cbc:CompanyID schemeID="0002">991192543</cbc:CompanyID></cac:PartyLegalEntity>
          </cac:Party></cac:AccountingSupplierParty>
          <cac:AccountingCustomerParty><cac:Party>
            <cac:PartyLegalEntity><cbc:CompanyID schemeID="0002">931473060</cbc:CompanyID></cac:PartyLegalEntity>
          </cac:Party></cac:AccountingCustomerParty>
        </Invoice>'''
        self.env['ir.attachment'].create({
            'name': 'selfbill.xml',
            'raw': xml,
            'mimetype': 'application/xml',
            'res_model': 'account.move',
            'res_id': move.id,
        })
        move._l10n_fr_pdp_transport_apply({'sender': '0225:931473060'})
        self.assertFalse(move.to_check)
        self.assertFalse(self._alert_bodies(move))
        # The seller (not the buyer) is sending a self-billed document: that is unexpected.
        move._l10n_fr_pdp_transport_apply({'sender': '0225:991192543'})
        self.assertTrue(move.to_check)
        self.assertIn('buyer', self._alert_bodies(move)[0])

    def test_transport_map_is_filled_from_get_all_documents(self):
        type(self).sender = '0225:931473060'
        transport_map = {}
        proxy_user = self.proxy_user.with_context(l10n_fr_pdp_transport_map=transport_map)
        proxy_user._make_request(
            proxy_user._get_server_url() + proxy_user._get_peppol_proxy_endpoint('1/get_all_documents'),
            params={},
        )
        self.assertEqual(transport_map, {
            MESSAGE_UUID: {'sender': '0225:931473060', 'receiver': self.receiver},
        })
        transport_map.clear()
        proxy_user._make_request(
            proxy_user._get_server_url() + proxy_user._get_peppol_proxy_endpoint('1/ack'),
            params={'message_uuids': []},
        )
        self.assertFalse(transport_map)

    def test_reviewer_gets_an_activity(self):
        self.env.company.l10n_fr_pdp_transport_alert_user_id = self.env.user
        move = self._receive(self.french_seller_xml, '0225:931473060')
        self.assertEqual(move.activity_ids.user_id, self.env.user)
        self.assertEqual(
            move.activity_ids.activity_type_id,
            self.env.ref('l10n_fr_pdp.mail_activity_transport_alert'),
        )

    def test_billing_mandate_removes_the_alert(self):
        move = self._create_flagged_move()
        self.assertEqual(move.l10n_fr_pdp_transport_alert_level, 'critical')
        move.partner_id.commercial_partner_id.l10n_fr_pdp_billing_mandate = True
        self.assertRecordValues(move, [{
            'l10n_fr_pdp_transport_alert_level': 'none',
            'l10n_fr_pdp_transport_needs_review': False,
        }])

    def test_action_post_requires_double_confirmation(self):
        move = self._create_flagged_move()
        action = move.action_post()
        self.assertEqual(move.state, 'draft')
        self.assertEqual(action['res_model'], 'l10n.fr.pdp.transport.confirm')
        wizard = self.env['l10n.fr.pdp.transport.confirm'].browse(action['res_id'])
        self.assertEqual(wizard.move_ids, move)
        self.assertEqual(wizard.alert_level, 'critical')
        wizard.action_confirm()
        self.assertEqual(move.state, 'posted')
        self.assertEqual(move.l10n_fr_pdp_transport_confirmed_uid, self.env.user)
        self.assertTrue(move.l10n_fr_pdp_transport_confirmed_date)
        self.assertFalse(move.l10n_fr_pdp_transport_needs_review)
        self.assertTrue(any('acknowledged' in (body or '') for body in move.message_ids.mapped('body')))

    def test_warning_wizard_is_not_critical(self):
        move = self._create_flagged_move(xml_content=self.original_xml)
        wizard = self.env['l10n.fr.pdp.transport.confirm'].browse(move.action_post()['res_id'])
        self.assertEqual(wizard.alert_level, 'warning')

    def test_skip_context_bypasses_the_check(self):
        move = self._create_flagged_move()
        move.with_context(l10n_fr_pdp_skip_transport_check=True).action_post()
        self.assertEqual(move.state, 'posted')

    def test_batch_post_only_holds_back_flagged_moves(self):
        flagged = self._create_flagged_move()
        clean = self._create_flagged_move(sender='0225:991192543')
        action = (flagged + clean).action_post()
        self.assertEqual(clean.state, 'posted')
        self.assertEqual(flagged.state, 'draft')
        self.assertEqual(
            self.env['l10n.fr.pdp.transport.confirm'].browse(action['res_id']).move_ids,
            flagged,
        )

    def test_unattended_post_is_blocked(self):
        move = self._create_flagged_move()
        move._post()
        self.assertEqual(move.state, 'draft')
        self.assertTrue(any('Auto-post was disabled' in (body or '') for body in move.message_ids.mapped('body')))

