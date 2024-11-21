from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFacturaeMisc(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('es')
    def setUpClass(cls):
        super().setUpClass()

    def test_es_suggested_invoice_edi_format(self):
        partner_es = self.env['res.partner'].create({
            'name': "ES partner",
            'country_id': self.env.ref('base.es').id,
        })
        partner_be = self.env['res.partner'].create({
            'name': "BE partner",
            'country_id': self.env.ref('base.be').id,
        })
        self.assertEqual(partner_es.invoice_edi_format, 'es_facturae')
        self.assertNotEqual(partner_be.invoice_edi_format, 'es_facturae')
