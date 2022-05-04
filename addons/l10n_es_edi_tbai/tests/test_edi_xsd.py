# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from lxml import etree
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import L10nEsTbaiXmlUtils
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommon


@tagged('external_l10n', 'post_install', '-at_install', '-standard', 'external')
class TestEdiTbaiXsds(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Download govt. XSDs (non deterministic, OK for non-standard tests)
        cls.env['ir.attachment']._l10n_es_tbai_load_xsd_attachments()

        cls.out_invoice = cls.env['account.move'].create({
            'name': 'INV/01',
            'move_type': 'out_invoice',
            'invoice_date': datetime.now(),
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': cls.product_a.id,
                'price_unit': 1000.0,
                'quantity': 5,
                'discount': 20.0,
                'tax_ids': [(6, 0, cls._get_tax_by_xml_id('s_iva21b').ids)],
            })],
        })

        cls.edi_format = cls.env.ref('l10n_es_edi_tbai.edi_es_tbai')

    def test_format_post(self):
        xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(self.out_invoice, cancel=False)

        # TODO validate for all tax agencies
        self._validate_format_xsd(
            xml_doc,
            f'l10n_es_edi_tbai.{self.env.company.l10n_es_tbai_tax_agency}_ticketBaiV1-2.xsd'
        )

    def test_format_cancel(self):
        self.out_invoice.l10n_es_tbai_registration_date = self.frozen_today  # currently values comes from attachment_edi (None here)

        xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(self.out_invoice, cancel=True)

        # TODO validate for all tax agencies
        self._validate_format_xsd(
            xml_doc,
            f'l10n_es_edi_tbai.{self.env.company.l10n_es_tbai_tax_agency}_Anula_ticketBaiV1-2.xsd'
        )

    def _validate_format_xsd(self, xml_doc, xsd_name):
        xml_bytes = etree.tostring(xml_doc, encoding="UTF-8")
        try:
            self.env.ref(xsd_name, raise_if_not_found=True)
            L10nEsTbaiXmlUtils._validate_format_xsd(xml_bytes, xsd_name, self.env)
        except (UserError, ValueError) as e:
            self.fail(str(e))
