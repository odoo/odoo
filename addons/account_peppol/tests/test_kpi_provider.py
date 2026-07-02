from itertools import product

from odoo.tests import tagged, TransactionCase
from odoo.tests.common import decorator


def main_company_countries(*country_codes):
    """ Decorate a method to execute it once for each given country """
    @decorator
    def _main_company_countries(func, *args, **kwargs):
        self = args[0]
        old_country_id = self.main_company.account_fiscal_country_id
        try:
            # retrieve countries
            Countries = self.env['res.country'].with_context(active_test=False)
            countries = {
                country.code: country
                for country in Countries.search([('code', 'in', list(country_codes))])
            }
            for country_code, country_id in countries.items():
                with self.subTest(country_code=country_code):
                    self.main_company.account_fiscal_country_id = country_id
                    func(*args, **kwargs)
                self.env.invalidate_all()
        finally:
            self.main_company.account_fiscal_country_id = old_country_id

    return _main_company_countries


@tagged('post_install', '-at_install')
class TestKpiProvider(TransactionCase):

    def setUp(self):
        super().setUp()

        self.main_company = self.env.ref('base.main_company')
        other_companies = self.env['res.company'].search([('id', '!=', self.main_company.id)])
        self.env['res.users'].search([('company_id', 'in', other_companies.ids)]).active = False
        other_companies.active = False

        self.expected_value_by_peppol_proxy_state = {
            'not_registered': 'not_done',
            'rejected': 'not_done',
            'canceled': 'not_done',
            'pending': 'incomplete',
            'active': 'done',
        }

    @main_company_countries('US', 'LU', 'IT', 'CN')
    def test_default_kpi_summary(self):
        self.assertCountEqual(self.env['kpi.provider'].get_account_peppol_kpi_summary(), [])

    def test_check_all_possible_peppol_proxy_states_are_covered(self):
        expected = {s[0] for s in self.env['res.company']._fields['account_peppol_proxy_state'].selection}
        actual = set(self.expected_value_by_peppol_proxy_state)
        self.assertEqual(actual, expected,
                         f"Missing states: {expected - actual}; "
                         f"Extra states: {actual - expected}")

    def test_kpi_summary_with_multiple_companies(self):
        other_company = self.env['res.company'].create({
            'name': 'Other LTD',
            'account_fiscal_country_id': self.ref('base.be'),
        })
        self.main_company.account_fiscal_country_id = self.env.ref('base.be')

        table_of_truth = {
            ('not_registered', 'not_registered'): 'not_done',
            ('not_registered', 'rejected'):       'not_done',
            ('not_registered', 'canceled'):       'not_done',
            ('not_registered', 'pending'):        'incomplete',
            ('not_registered', 'active'):         'incomplete',

            ('rejected', 'not_registered'):       'not_done',
            ('rejected', 'rejected'):             'not_done',
            ('rejected', 'canceled'):             'not_done',
            ('rejected', 'pending'):              'incomplete',
            ('rejected', 'active'):               'incomplete',

            ('canceled', 'not_registered'):       'not_done',
            ('canceled', 'rejected'):             'not_done',
            ('canceled', 'canceled'):             'not_done',
            ('canceled', 'pending'):              'incomplete',
            ('canceled', 'active'):               'incomplete',

            ('pending', 'not_registered'):        'incomplete',
            ('pending', 'rejected'):              'incomplete',
            ('pending', 'canceled'):              'incomplete',
            ('pending', 'pending'):               'incomplete',
            ('pending', 'active'):                'incomplete',

            ('active', 'not_registered'):         'incomplete',
            ('active', 'rejected'):               'incomplete',
            ('active', 'canceled'):               'incomplete',
            ('active', 'pending'):                'incomplete',
            ('active', 'active'):                 'done',
        }

        actual_keys = set(table_of_truth)
        expected_keys = set(product((s[0] for s in self.env['res.company']._fields['account_peppol_proxy_state'].selection), repeat=2))
        self.assertEqual(actual_keys, expected_keys,
                         f"Missing table of truth keys: {expected_keys - actual_keys}; "
                         f"Extra table of truth keys: {actual_keys - expected_keys}")

        for (proxy_state1, proxy_state2), expected_value in table_of_truth.items():
            with self.subTest(proxy_state1=proxy_state1, proxy_state2=proxy_state2):
                self.main_company.account_peppol_proxy_state = proxy_state1
                other_company.account_peppol_proxy_state = proxy_state2

                self.assertCountEqual(self.env['kpi.provider'].get_account_peppol_kpi_summary(), [{
                    'id': 'account_peppol.proxy_state',
                    'name': 'KYC',
                    'type': 'kyc_status',
                    'value': expected_value,
                }])

    @main_company_countries('BE')
    def test_kpi_summary_peppol_proxy_states_be(self):
        for proxy_state, expected_value in self.expected_value_by_peppol_proxy_state.items():
            with self.subTest(proxy_state=proxy_state):
                self.main_company.account_peppol_proxy_state = proxy_state

                self.assertCountEqual(self.env['kpi.provider'].get_account_peppol_kpi_summary(), [{
                    'id': 'account_peppol.proxy_state',
                    'name': 'KYC',
                    'type': 'kyc_status',
                    'value': expected_value,
                }])
