# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from .common import TestEsEdiCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiWebServices(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Invoice name are tracked by the web-services so this constant tries to get a new unique invoice name at each
        # execution.
        cls.today = datetime.now()
        cls.time_name = cls.today.strftime('%H%M%S')

        cls.out_invoice = cls.env['account.move'].create({
            'name': f'INV{cls.time_name}',
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })
        cls.out_invoice.action_post()

        cls.in_invoice = cls.env['account.move'].create({
            'name': f'BILL{cls.time_name}',
            'ref': f'REFBILL{cls.time_name}',
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': fields.Date.to_string(cls.today.date()),
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('p_iva10_bc').ids)],
            })],
        })
        cls.in_invoice.action_post()

    def test_edi_gipuzkoa(self):
        self.env.company.l10n_es_sii_tax_agency = 'gipuzkoa'

        self.out_invoice._send_l10n_es_sii_document()
        self.in_invoice._send_l10n_es_sii_document()

        self.assertEqual(self.out_invoice.l10n_es_edi_sii_state, 'sent')
        self.assertEqual(self.in_invoice.l10n_es_edi_sii_state, 'sent')

    def test_edi_bizkaia(self):
        self.env.company.l10n_es_sii_tax_agency = 'bizkaia'

        self.out_invoice._send_l10n_es_sii_document()
        self.in_invoice._send_l10n_es_sii_document()

        self.assertEqual(self.out_invoice.l10n_es_edi_sii_state, 'sent')
        self.assertEqual(self.in_invoice.l10n_es_edi_sii_state, 'sent')

    def _mock_sii_fault(self, document_instance, communication_type, info_list):
        """ This cleanly mocks the return value of _post_to_agency when our specific Exception is caught """
        return {
            doc: (False, {
                'response_message': 'Fault error:\n[9120] Valor DE322038342 o tipo incorrecto del campo: NIF',
                'is_soap_fault': True
            })
            for doc in document_instance
        }

    def test_sii_soap_fault_sets_document_to_cancelled(self):
        """ Test that a hard SOAP fault correctly sets state to 'cancelled' to prevent infinite cron loops. """

        purchase_journal = self.company_data['default_journal_purchase']
        purchase_tax = self._get_tax_by_xml_id('p_iva10_bc')

        fault_invoice = self._create_invoice_one_line(
            move_type='in_invoice',
            ref='TEST_REF_123',
            journal_id=purchase_journal,
            partner_id=self.partner_a,
            invoice_date='2024-01-01',
            product_id=self.product_a,
            tax_ids=purchase_tax,
            post=True,
        )

        with patch(
            'odoo.addons.l10n_es_edi_sii.models.l10n_es_edi_sii_document.L10nEsEdiSiiDocument._post_to_agency',
            autospec=True,
            side_effect=self._mock_sii_fault,
        ):
            self.env.ref('l10n_es_edi_sii.action_l10n_es_send_sii').with_context(
                active_model='account.move', active_ids=fault_invoice.ids,
            ).run()

        document = fault_invoice.l10n_es_edi_sii_document_ids

        self.assertTrue(document, "The SII document should have been created.")
        self.assertEqual(document.state, 'cancelled')

        self.assertIn("9120", document.response_message)
        self.assertIn("NIF", document.response_message)
