# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nTHFiscalPosition(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('th')
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template']
        cls.fpos_domestic_company = ChartTemplate.ref('l10n_th_fiscal_position_template_1')
        cls.fpos_domestic_individual = ChartTemplate.ref('l10n_th_fiscal_position_template_2')
        cls.tax_wht_individual = ChartTemplate.ref('tax_wht_pers_3')
        cls.tax_wht_company = ChartTemplate.ref('tax_wht_co_3')

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

    def _get_fiscal_position(self, partner):
        return self.env['account.fiscal.position']._get_fiscal_position(partner)

    def test_fiscal_position_th_company(self):
        fpos = self._get_fiscal_position(self.partner_th_company)
        self.assertEqual(fpos, self.fpos_domestic_company)
        self.assertEqual(fpos.map_tax(self.tax_wht_individual), self.tax_wht_company)

    def test_fiscal_position_th_company_contact(self):
        """ A contact of a company is not a company itself, but follows its company. """
        contact = self.env['res.partner'].create({
            'name': 'TH Company Contact',
            'parent_id': self.partner_th_company.id,
        })
        self.assertFalse(contact.is_company)
        self.assertEqual(self._get_fiscal_position(contact), self.fpos_domestic_company)

    def test_fiscal_position_th_individual_with_citizen_id(self):
        """ The citizen ID of an individual is a Tax ID, but not the one of a company. """
        fpos = self._get_fiscal_position(self.partner_th_individual)
        self.assertEqual(fpos, self.fpos_domestic_individual)
        self.assertEqual(fpos.map_tax(self.tax_wht_company), self.tax_wht_individual)
