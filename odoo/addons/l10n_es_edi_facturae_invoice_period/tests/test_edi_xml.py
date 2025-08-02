import lxml
from freezegun.api import freeze_time

from odoo.tests import tagged
from odoo.tools import file_open

from odoo.addons.l10n_es_edi_facturae.tests.test_edi_xml import TestEdiFacturaeXmls


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestEdiFacturaeInvoicePeriodXmls(TestEdiFacturaeXmls):

    @freeze_time('2023-01-01')
    def test_generate_with_invoice_period(self):
        invoice = self.create_invoice(
            partner_id=self.partner_a.id,
            move_type='out_invoice',
            invoice_line_ids=[{'price_unit': 100.0, 'tax_ids': [self.tax.id]}],
            l10n_es_invoicing_period_start_date='2023-01-01',
            l10n_es_invoicing_period_end_date='2023-01-31',
        )
        invoice.action_post()
        generated_file, errors = invoice._l10n_es_edi_facturae_render_facturae()
        self.assertFalse(errors)
        self.assertTrue(generated_file)

        with file_open('l10n_es_edi_facturae_invoice_period/tests/data/expected_invoice_period_document.xml', 'rt') as f:
            expected_xml = lxml.etree.fromstring(f.read().encode())
        self.assertXmlTreeEqual(lxml.etree.fromstring(generated_file), expected_xml)
