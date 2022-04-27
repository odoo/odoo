# -*- coding: utf-8 -*-
from datetime import datetime

from odoo.tests import tagged
from odoo import fields
from .common import TestEsEdiCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiWebServices(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_es.account_chart_template_full', edi_format_ref='l10n_es_edi_sii.edi_es_sii'):
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)

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

        cls.moves = cls.out_invoice + cls.in_invoice

    def test_edi_aeat(self):
        self.env.company.l10n_es_edi_tax_agency = 'aeat'

        self.moves.action_process_edi_web_services(with_commit=False)
        generated_files = self._process_documents_web_services(self.moves, {'es_sii'})
        self.assertTrue(generated_files)
        self.assertRecordValues(self.out_invoice, [{'edi_state': 'sent'}])
        self.assertRecordValues(self.in_invoice, [{'edi_state': 'sent'}])

    def test_edi_gipuzkoa(self):
        self.env.company.l10n_es_edi_tax_agency = 'gipuzkoa'

        self.moves.action_process_edi_web_services(with_commit=False)
        generated_files = self._process_documents_web_services(self.moves, {'es_sii'})
        self.assertTrue(generated_files)
        self.assertRecordValues(self.out_invoice, [{'edi_state': 'sent'}])
        self.assertRecordValues(self.in_invoice, [{'edi_state': 'sent'}])

    def test_edi_bizkaia(self):
        self.env.company.l10n_es_edi_tax_agency = 'bizkaia'

        self.moves.action_process_edi_web_services(with_commit=False)
        generated_files = self._process_documents_web_services(self.moves, {'es_sii'})
        self.assertTrue(generated_files)
        self.assertRecordValues(self.out_invoice, [{'edi_state': 'sent'}])
        self.assertRecordValues(self.in_invoice, [{'edi_state': 'sent'}])
