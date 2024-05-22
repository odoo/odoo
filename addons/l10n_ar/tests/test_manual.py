# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import common
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestManual(common.TestAr):

    @classmethod
    def setUpClass(cls):
        super(TestManual, cls).setUpClass()
        cls.journal = cls._create_journal(cls, 'preprinted')
        cls.partner = cls.res_partner_adhoc
        cls._create_test_invoices_like_demo(cls)

    def test_01_create_invoice(self):
        """ Create and validate an invoice for a Responsable Inscripto

        * Proper set the current user company
        * Properly set the tax amount of the product / partner
        * Proper fiscal position (this case not fiscal position is selected)
        """
        invoice = self._create_invoice()
        self.assertEqual(invoice.company_id, self.company_ri, 'created with wrong company')
        self.assertEqual(invoice.amount_tax, 21, 'invoice taxes are not properly set')
        self.assertEqual(invoice.amount_total, 121.0, 'invoice taxes has not been applied to the total')
        self.assertEqual(invoice.l10n_latam_document_type_id, self.document_type['invoice_a'], 'selected document type should be Factura A')
        self._post(invoice)
        self.assertEqual(invoice.state, 'posted', 'invoice has not been validate in Odoo')
        self.assertEqual(invoice.name, 'FA-A %05d-00000002' % self.journal.l10n_ar_afip_pos_number, 'Invoice number is wrong')

    def test_02_fiscal_position(self):
        # ADHOC SA > IVA Responsable Inscripto > Without Fiscal Positon
        invoice = self._create_invoice({'partner': self.partner})
        self.assertFalse(invoice.fiscal_position_id, 'Fiscal position should be set to empty')

        # Consumidor Final > IVA Responsable Inscripto > Without Fiscal Positon
        invoice = self._create_invoice({'partner': self.partner_cf})
        self.assertFalse(invoice.fiscal_position_id, 'Fiscal position should be set to empty')

        # Cerro Castor > IVA Liberado – Ley Nº 19.640 > Compras / Ventas Zona Franca > IVA Exento
        invoice = self._create_invoice({'partner': self.res_partner_cerrocastor})
        self.assertEqual(invoice.fiscal_position_id, self._search_fp('Compras / Ventas Zona Franca'))

        # Expresso > Cliente / Proveedor del Exterior >  > IVA Exento
        invoice = self._create_invoice({'partner': self.res_partner_expresso})
        self.assertEqual(invoice.fiscal_position_id, self._search_fp('Compras / Ventas al exterior'))

    def test_03_corner_cases(self):
        """ Mono partner of type Service and VAT 21 """
        self._post(self.demo_invoices['test_invoice_1'])

    def test_04_corner_cases(self):
        """ Exento partner with multiple VAT types 21, 27 and 10,5' """
        self._post(self.demo_invoices['test_invoice_2'])

    def test_05_corner_cases(self):
        """ RI partner with VAT 0 and 21 """
        self._post(self.demo_invoices['test_invoice_3'])

    def test_06_corner_cases(self):
        """ RI partner with VAT exempt and 21 """
        self._post(self.demo_invoices['test_invoice_4'])

    def test_07_corner_cases(self):
        """ RI partner with all type of taxes """
        self._post(self.demo_invoices['test_invoice_5'])

    def test_08_corner_cases(self):
        """ Consumidor Final """
        self._post(self.demo_invoices['test_invoice_8'])

    def test_09_corner_cases(self):
        """ RI partner with many lines in order to prove rounding error, with 4  decimals of precision for the
        currency and 2 decimals for the product the error appear """
        self._post(self.demo_invoices['test_invoice_11'])

    def test_10_corner_cases(self):
        """ RI partner with many lines in order to test rounding error, it is required  to use a 4 decimal precision
        in product in order to the error occur """
        self._post(self.demo_invoices['test_invoice_12'])

    def test_11_corner_cases(self):
        """ RI partner with many lines in order to test zero amount  invoices y rounding error. it is required to
        set the product decimal precision to 4 and change 260,59 for 260.60 in order to reproduce the error """
        self._post(self.demo_invoices['test_invoice_13'])

    def test_12_corner_cases(self):
        """ RI partner with 100%% of discount """
        self._post(self.demo_invoices['test_invoice_17'])

    def test_13_corner_cases(self):
        """ RI partner with 100%% of discount and with different VAT aliquots """
        self._post(self.demo_invoices['test_invoice_18'])

    def test_14_corner_cases(self):
        """ Responsable Inscripto" in USD and VAT 21 """
        self._prepare_multicurrency_values()
        self._post(self.demo_invoices['test_invoice_10'])
