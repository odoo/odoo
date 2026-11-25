# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFiscalPositionSKR04(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('de_skr04')
    def setUpClass(cls):
        super().setUpClass()
        ChartTemplate = cls.env['account.chart.template'].with_company(cls.company_data['company'])
        cls.fpos_domestic = ChartTemplate.ref('fiscal_position_domestic_skr04')
        cls.fpos_eu_vat_id = ChartTemplate.ref('fiscal_position_eu_vat_id_partner_skr04')
        cls.fpos_eu_vat_id_service = ChartTemplate.ref('fiscal_position_eu_vat_id_partner_service_skr04')

    def _get_fiscal_position(self, country_code, vat=False):
        partner = self.env['res.partner'].create({
            'name': f'Partner {country_code} {vat or "without VAT"}',
            'country_id': self.env.ref(f'base.{country_code.lower()}').id,
            'vat': vat,
        })
        return self.env['account.fiscal.position']._get_fiscal_position(partner)

    def test_eu_vat_id_fiscal_positions_require_vat(self):
        """ The "with VAT ID" EU fiscal positions must require a VAT number, as in SKR03. """
        self.assertTrue(self.fpos_eu_vat_id.vat_required)
        self.assertTrue(self.fpos_eu_vat_id_service.vat_required)

    def test_eu_fiscal_position_auto_apply(self):
        """ The intra-EU fiscal position is only applied to EU partners having a VAT number. """
        self.assertEqual(self._get_fiscal_position('FR', 'FR23334175221'), self.fpos_eu_vat_id)
        self.assertFalse(self._get_fiscal_position('FR'))

    def test_domestic_fiscal_position_auto_apply(self):
        """ A german partner never gets the intra-EU fiscal position, with or without VAT number. """
        self.assertEqual(self._get_fiscal_position('DE', 'DE123456788'), self.fpos_domestic)
        self.assertFalse(self._get_fiscal_position('DE'))
