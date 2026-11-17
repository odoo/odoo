# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import TransactionCase, tagged

EXPECTED_SRU_TYPE = {'se_K1': 'ne', 'se_K2': 'ink2', 'se_K3': 'ink2', 'se_K2_HB': 'ink4', 'se_K2_NPO': 'ink3'}


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSeSruType(TransactionCase):
    """The SRU form follows the chart of accounts and can be chosen per company."""

    def _install(self, template_code):
        company = self.env['res.company'].create({
            'name': f'SE {template_code}',
            'country_id': self.env.ref('base.se').id,
        })
        self.env.user.company_ids |= company
        self.env['account.chart.template'].try_loading(template_code, company, install_demo=False)
        return company

    def test_sru_type_derived_from_template(self):
        mapping_model = self.env['l10n_se.sru.mapping']
        for template_code, sru_type in EXPECTED_SRU_TYPE.items():
            with self.subTest(template=template_code):
                company = self._install(template_code)
                self.assertEqual(company.l10n_se_sru_type, sru_type, "defaults from the chart of accounts")
                self.assertEqual(mapping_model._get_sru_type(company), sru_type)
                self.assertEqual(mapping_model._get_sru_type(company, 'ink3'), 'ink3')

    def test_sru_type_chosen_on_company(self):
        """A form chosen in Settings (e.g. INK3 for a foundation) wins over the chart default."""
        company = self._install('se_K2')
        company.l10n_se_sru_type = 'ink3'
        self.assertEqual(self.env['l10n_se.sru.mapping']._get_sru_type(company), 'ink3')
        settings = self.env['res.config.settings'].with_company(company).create({})
        self.assertEqual(settings.l10n_se_sru_type, 'ink3')
        settings.action_l10n_se_load_sru_mapping()
        mappings = self.env['l10n_se.sru.mapping'].search([('company_id', '=', company.id)])
        self.assertTrue(mappings)
        self.assertEqual(set(mappings.mapped('sru_type')), {'ink3'})
