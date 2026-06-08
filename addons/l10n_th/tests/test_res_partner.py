from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTHTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_th_company = cls.env['res.partner'].create({
            'name': 'TH Company',
            'vat': '0107537002443',
            'country_id': cls.env.ref('base.th').id,
        })

        cls.partner_th_individual = cls.env['res.partner'].create({
            'name': 'TH Individual',
            'vat': '1103900016621',
            'country_id': cls.env.ref('base.th').id,
        })

    def test_is_company_th(self):
        self.assertTrue(
            self.partner_th_company.is_company,
            "TH Partner with VAT starting with '0' should be treated as a company.",
        )
        self.assertFalse(
            self.partner_th_individual.is_company,
            "TH Partner with VAT not starting with '0' should be treated as an individual.",
        )
