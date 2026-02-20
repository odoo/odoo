# -*- coding: utf-8 -*-
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged
from .common import TestEsEdiCommon
from odoo.addons.l10n_es_edi_sii.models.account_move import AccountMove


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

        with patch.object(AccountMove, '_l10n_es_edi_call_web_service_sign', autospec=True) as mock_sign:
            mock_sign.side_effect = lambda move, info_list, cancel=False: {'success': True}

            self.out_invoice._send_l10n_es_invoice()
            self.in_invoice._send_l10n_es_invoice()

        self.assertEqual(self.out_invoice.l10n_es_edi_sii_state, 'sent')
        self.assertEqual(self.in_invoice.l10n_es_edi_sii_state, 'sent')

    def test_edi_bizkaia(self):
        self.env.company.l10n_es_sii_tax_agency = 'bizkaia'

        with patch.object(AccountMove, '_l10n_es_edi_call_web_service_sign', autospec=True) as mock_sign:
            mock_sign.side_effect = lambda move, info_list, cancel=False: {'success': True}

            self.out_invoice._send_l10n_es_invoice()
            self.in_invoice._send_l10n_es_invoice()

        self.assertEqual(self.out_invoice.l10n_es_edi_sii_state, 'sent')
        self.assertEqual(self.in_invoice.l10n_es_edi_sii_state, 'sent')
