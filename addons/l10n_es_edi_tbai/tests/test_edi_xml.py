# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from freezegun import freeze_time
from lxml import etree
from odoo.addons.l10n_es_edi_tbai.models.xml_utils import L10nEsTbaiXmlUtils
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiTbaiXmls(TestEsEdiTbaiCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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

    def test_xml_tree_post(self):
        with freeze_time(self.frozen_today):
            xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(self.out_invoice, cancel=False)
            xml_doc.remove(xml_doc.find("ds:Signature", namespaces=L10nEsTbaiXmlUtils.NS_MAP))
            xml_expected = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_POST)
            self.assertXmlTreeEqual(xml_doc, xml_expected)

    def test_xml_tree_cancel(self):
        self.out_invoice.l10n_es_tbai_registration_date = self.frozen_today
        xml_doc = self.edi_format._get_l10n_es_tbai_invoice_xml(self.out_invoice, cancel=True)
        xml_doc.remove(xml_doc.find("ds:Signature", namespaces=L10nEsTbaiXmlUtils.NS_MAP))
        xml_expected = etree.fromstring(super().L10N_ES_TBAI_SAMPLE_XML_CANCEL)
        self.assertXmlTreeEqual(xml_doc, xml_expected)
