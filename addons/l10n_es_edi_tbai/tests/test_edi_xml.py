# coding: utf-8
import base64
import io

from lxml import etree
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.xml_utils import _check_with_xsd

from .common import TestEsEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiXmls(TestEsEdiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.attachment']._l10n_es_tbai_load_xsd_attachments()  # Gov. XSD download

        cls.out_invoice = cls.env['account.move'].create({
            'name': 'INV/01',
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

        cls.edi_format = cls.env['account.edi.format'].search([
            ('code', '=', 'es_tbai')
        ])

    def test_format_post(self):
        xml_doc = self.edi_format._l10n_es_tbai_get_invoice_xml(self.out_invoice, cancel=False)

        # TODO validate for all tax agencies
        self._validate_format_xsd(
            xml_doc,
            f'l10n_es_edi_tbai.{self.env.company.l10n_es_tbai_tax_agency}_ticketBaiV1-2.xsd'
        )

    def test_format_cancel(self):
        xml_doc = self.edi_format._l10n_es_tbai_get_invoice_xml(self.out_invoice, cancel=True)

        # TODO validate for all tax agencies
        self._validate_format_xsd(
            xml_doc,
            f'l10n_es_edi_tbai.{self.env.company.l10n_es_tbai_tax_agency}_Anula_ticketBaiV1-2.xsd'
        )

    def _validate_format_xsd(self, xml_doc, xsd_name):
        xml_bytes = etree.tostring(xml_doc, encoding="UTF-8")
        try:
            self.env['l10n_es.edi.tbai.util'].validate_format_xsd(xml_bytes, xsd_name)
        except UserError as e:
            self.fail(str(e))
