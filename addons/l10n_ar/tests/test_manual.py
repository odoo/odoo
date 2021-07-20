# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import common
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestManual(common.TestAR):

    @classmethod
    def setUpClass(cls):
        super(TestManual, cls).setUpClass()
        cls.journal = cls._create_journal(cls, 'preprinted')
        cls.partner = cls.partner_ri

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
        self.assertEqual(invoice.name, 'FA-A %05d-00000001' % self.journal.l10n_ar_afip_pos_number, 'Invoice number is wrong')

    def test_02_fiscal_position(self):
        # ADHOC SA > IVA Responsable Inscripto > Without Fiscal Positon
        invoice = self._create_invoice({'partner': self.partner_ri})
        self.assertFalse(invoice.fiscal_position_id, 'Fiscal position should be set to empty')

        # Consumidor Final > IVA Responsable Inscripto > Without Fiscal Positon
        invoice = self._create_invoice({'partner': self.partner_cf})
        self.assertFalse(invoice.fiscal_position_id, 'Fiscal position should be set to empty')

        # Cerro Castor > IVA Liberado – Ley Nº 19.640 > Compras / Ventas Zona Franca > IVA Exento
        invoice = self._create_invoice({'partner': self.partner_fz})
        self.assertEqual(invoice.fiscal_position_id, self._search_fp('Compras / Ventas Zona Franca'))

        # Expresso > Cliente / Proveedor del Exterior >  > IVA Exento
        invoice = self._create_invoice({'partner': self.partner_ex})
        self.assertEqual(invoice.fiscal_position_id, self._search_fp('Compras / Ventas al exterior'))

    def test_03_afip_concept(self):
        # Products / Definitive export of goods
        invoice = self._create_invoice()
        self.assertEqual(invoice.l10n_ar_afip_concept, '1', 'The correct AFIP Concept should be: Concept should be: Products / Definitive export of goods')

        # Services
        invoice = self._create_invoice({'lines': [{'product': self.service_iva_27}]})
        self.assertEqual(invoice.l10n_ar_afip_concept, '2', 'The correct AFIP Concept should be: Services')

        # Product and services
        invoice = self._create_invoice({'lines': [{'product': self.service_iva_27}, {'product': self.product_iva_21}]})
        self.assertEqual(invoice.l10n_ar_afip_concept, '3', 'The correct AFIP Concept should be: Products and Services')

    def test_20_corner_cases(self):
        # TODO copy the ones created in l10n?ar as corner cases and run it
        cases = {'demo_invoice_1': '"Mono" partner of tipe Service and VAT 21',
                 'demo_invoice_2': '"Exento" partner with multiple VAT types 21, 27 and 10,5',
                 'demo_invoice_3': '"RI" partner with VAT 0 and 21',
                 'demo_invoice_4': '"RI" partner with VAT exempt and 21',
                 'demo_invoice_5': '"RI" partner with all type of taxes',
                 'demo_invoice_8': '"Consumidor Final"',
                 'demo_invoice_11': '"RI" partner with many lines in order to prove rounding error, with 4'
                 ' decimals of precision for the currency and 2 decimals for the product the error apperar',
                 'demo_invoice_12': '"RI" partner with many lines in order to test rounding error, it is required'
                 ' to use a 4 decimal precision in prodct in order to the error occur',
                 'demo_invoice_13': '"RI" partner with many lines in order to test zero amount'
                 ' invoices y rounding error. it is required to set the product decimal precision to 4 and change 260.59'
                 ' for 260.60 in order to reproduce the error',
                 'demo_invoice_17': '"RI" partner with 100%% of discount',
                 'demo_invoice_18': '"RI" partner with 100%% of discount and with different VAT aliquots'}
        self._test_demo_cases(cases)

    def test_21_currency(self):
        self._prepare_multicurrency_values()
        self._test_demo_cases({'demo_invoice_10': '"Responsable Inscripto" in USD and VAT 21'})
