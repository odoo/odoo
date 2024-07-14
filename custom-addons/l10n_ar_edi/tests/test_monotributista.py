# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged
from . import common


@tagged('-at_install', 'external_l10n', 'post_install', '-standard', 'external')
class TestMono(common.TestEdi):

    @classmethod
    def setUpClass(cls, afip_ws):
        # Issue ['C', 'E'] and  Receive ['B', 'C', 'I']
        super(TestMono, cls).setUpClass(afip_ws)
        # Login in "Monotributista" Company
        cls.env.user.write({'company_id': cls.company_mono.id})
        cls._create_afip_connections(cls, cls.company_mono, afip_ws, 'test_cert2.crt')


@tagged('fe', 'mono', 'external_l10n', '-at_install', 'post_install', '-standard', 'external')
class TestFE(TestMono):

    @classmethod
    def setUpClass(cls):
        super(TestFE, cls).setUpClass('wsfe')
        cls.partner = cls.res_partner_adhoc
        cls.journal = cls._create_journal(cls, 'wsfe')
        cls.document_type.update({
            'invoice_c': cls.env.ref('l10n_ar.dc_c_f'),
            'debit_note_c': cls.env.ref('l10n_ar.dc_c_nd'),
            'credit_note_c': cls.env.ref('l10n_ar.dc_c_nc'),
        })

    def test_00_connection(self):
        self._test_connection()

    def test_01_consult_invoice(self):
        self._test_consult_invoice()

    def test_02_invoice_c_product(self):
        self._test_case('invoice_c', 'product')

    def test_03_invoice_c_service(self):
        self._test_case('invoice_c', 'service')

    def test_04_invoice_c_product_service(self):
        self._test_case('invoice_c', 'product_service')

    def test_05_debit_note_c_product(self):
        invoice = self._test_case('invoice_c', 'product')
        self._test_case_debit_note('debit_note_c', invoice)

    def test_06_debit_note_c_service(self):
        invoice = self._test_case('invoice_c', 'service')
        self._test_case_debit_note('debit_note_c', invoice)

    def test_06_debit_note_c_product_service(self):
        invoice = self._test_case('invoice_c', 'product_service')
        self._test_case_debit_note('debit_note_c', invoice)

    def test_07_credit_note_c_product(self):
        invoice = self._test_case('invoice_c', 'product')
        self._test_case_credit_note('credit_note_c', invoice)

    def test_08_credit_note_c_service(self):
        invoice = self._test_case('invoice_c', 'service')
        self._test_case_credit_note('credit_note_c', invoice)

    def test_09_credit_note_c_product_service(self):
        invoice = self._test_case('invoice_c', 'product_service')
        self._test_case_credit_note('credit_note_c', invoice)


# @tagged('fe', 'mono', 'external_l10n', '-at_install', 'post_install', '-standard', 'external')
# class TestMiPyME(TestMono):

#     @classmethod
#     def setUpClass(cls):
#         super(TestMiPyME, cls).setUpClass('wsfe')
#         cls.partner = cls.res_partner_adhoc
#         cls.journal = cls._create_journal(cls, 'wsfe')
#         cls.document_type.update({
#             'invoice_mipyme_c': cls.env.ref('l10n_ar.dc_fce_c_f')})

#     def test_10_invoice_mipyme_c_product(self):
#         self._test_case('invoice_mipyme_c', 'product')

#     def test_11_invoice_mipyme_c_service(self):
#         self._test_case('invoice_mipyme_c', 'service')

#     def test_12_invoice_mipyme_c_product_service(self):
#         self._test_case('invoice_mipyme_c', 'product_service')


# @tagged('fex', 'mono', 'external_l10n', '-at_install', 'post_install', '-standard', 'external')
# class TestFEX(common.TestFex, TestMono):

#     def test_01_invoice_e_product(self):
#         self._test_case('invoice_e', 'product')

#     def test_02_invoice_e_service(self):
#         self._test_case('invoice_e', 'service')

#     def test_03_invoice_e_product_service(self):
#         self._test_case('invoice_e', 'product_service')
