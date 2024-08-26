from odoo.addons.l10n_eu_oss.tests.test_oss import OssTemplateTestCase
from odoo.addons.l10n_extra_eu_oss.models.extra_eu_tax_map import EXTRA_EU_TAX_MAP
from odoo.tests import tagged


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestIOSSUnitedKingdom(OssTemplateTestCase):

    @classmethod
    def setUpClass(cls, chart_template_ref='l10n_uk.l10n_uk'):
        cls.load_specific_chart_template(chart_template_ref)
        cls.company_data['company'].country_id = cls.env.ref('base.uk')
        cls.company_data['company']._map_extra_eu_taxes()

    def test_company_fiscal_positions(self):
        """
        This test ensure that the fiscal positions are correctly set for the company.
        """
        # get an eu country which isn't the current one:
        eu_country = self.env.ref('base.europe').country_ids[0]
        fiscal_position = self.env['account.fiscal.position'].search([
            ('company_id', '=', self.company_data['company'].id),
            ('country_id', '=', eu_country.id)
        ], limit=1)

        self.assertEqual(fiscal_position.name, 'IOSS B2C %s' % eu_country.name)
        self.assertEqual(fiscal_position.tax_ids[0].tax_src_id.amount, 20.0)
        self.assertEqual(fiscal_position.tax_ids[0].tax_dest_id.amount, EXTRA_EU_TAX_MAP.get(('GB', 20.0, '%s' % eu_country.code)))
