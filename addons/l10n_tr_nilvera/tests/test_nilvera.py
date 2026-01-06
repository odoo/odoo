from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTRNilveraTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.write({
            'name': 'TR Company',
            'vat': '1729171602',
            'street': '3281. Cadde',
            'street2': 'Mavişehir Sokak, 5. Kat',
            'city': 'İç Anadolu Bölgesi',
            'country_id': cls.env.ref('base.tr').id,
            'state_id': cls.env.ref('base.state_tr_81').id,
            'zip': '06810',
            'phone': '+90 501 234 56 78',
            'invoice_edi_format': 'ubl_tr',
        })

        cls.partner_a.write({
            'name': 'Başhisar Elektronik ve Hizmetler A.Ş.',
            'vat': '17291716060',
            'street': 'Üçhisar Mahallesi',
            'street2': 'Kaya Sokak No: 15',
            'city': 'Ürgüp',
            'country_id': cls.env.ref('base.tr').id,
            'state_id': cls.env.ref('base.state_tr_50').id,
            'zip': '50240',
            'phone': '+90 509 987 12 34',
            'invoice_edi_format': 'ubl_tr',
        })

    def test_tr_nilvera_company_definition(self):
        """
        Ensure UBL TR Partners are categorized correctly based on Tax ID length:
            - VKN (Company): 10 digits
            - TCKN (Individual): 11 digits
        """
        self.assertFalse(self.partner_a.is_company, "UBL Tr Partner with an 11-digit Vat should be treated as an individual.")
        self.assertTrue(self.partner_b.is_company, "ULB Tr Partner with a 10-digit Vat should be treated as a company.")
