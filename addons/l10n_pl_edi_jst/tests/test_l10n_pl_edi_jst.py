from lxml import etree

from odoo import tools
from odoo.tests import freeze_time, tagged

from odoo.addons.l10n_pl_edi.tests.test_l10n_pl_edi import TestL10nPlEdi


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPlEdiJst(TestL10nPlEdi):

    @classmethod
    @freeze_time('2026-01-23')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_pl_jst = cls.env['res.partner'].create({
            'name': 'Krakow Municipality',
            'is_company': True,
            'country_id': cls.country_pl.id,
            'vat': 'PL9999999999',
            'street': 'Municipality St. 9',
            'city': 'Krakow',
            'zip': '30-001',
        })
        cls.partner_pl.l10n_pl_parent_lgu = cls.partner_pl_jst

    @freeze_time('2026-01-23')
    def test_invoice_with_jst(self):
        self.standard_invoice.action_post()
        path = "l10n_pl_edi_jst/tests/export_xmls/standert_fa3_format_with_jst.xml"
        with tools.file_open(path, mode='rb') as fd:
            expected_tree = etree.fromstring(fd.read())
        xml = self.standard_invoice._l10n_pl_edi_render_xml()
        invoice_etree = etree.fromstring(xml)
        try:
            self.assertXmlTreeEqual(invoice_etree, expected_tree)
        except AssertionError as ae:
            ae.args = (ae.args[0] + f"\nFile used for comparison: {path}", )
            raise
