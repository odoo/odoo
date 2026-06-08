from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nMYTest(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a.write({
            'name': 'Başhisar Elektronik dan Perkhidmatan Sdn. Bhd.',
            'vat': 'IG115002000',
            'street': 'Jalan Tun Razak 15',
            'street2': 'Suite 8-3, Wisma Sentral',
            'city': 'Johor Bahru',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'zip': '80000',
            'phone': '+60 13-987 2489',
        })

        cls.partner_b.write({
            'name': 'MY Company',
            'vat': 'C20880050010',
            'street': 'Jalan Ampang 3281',
            'street2': 'Level 5, Menara Mutiara',
            'city': 'Kuala Lumpur',
            'country_id': cls.env.ref('base.my').id,
            'state_id': cls.env.ref('base.state_my_jhr').id,
            'zip': '06810',
            'phone': '+60 12-345 8899'
        })

    def test_my_company_definition(self):
        """
        Ensure MY Partners are categorized correctly based on Tax ID:
            - (Company): TIN not start with IG
            - (Individual): TIN start with IG
        """
        self.assertFalse(self.partner_a.is_company, "MY Partner with a VAT starting with 'IG' should be treated as an individual.")
        self.assertTrue(self.partner_b.is_company, "MY Partner with a VAT not starting with 'IG' should be treated as a company.")
