
from odoo.tests.common import tagged, HttpCase

from .common import DashboardTestCommon


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestDashboardController(DashboardTestCommon, HttpCase):

    def test_load_with_user_locale(self):
        self.authenticate(self.user.login, self.user.password)
        dashboard = self.create_dashboard().with_user(self.user)
        self.user.lang = 'en_US'

        response = self.url_open(f'/spreadsheet/dashboard/data/{dashboard.id}')
        data = response.json()
        locale = data['snapshot']['settings']['locale']
        self.assertEqual(locale['code'], 'en_US')
        self.assertEqual(len(data['revisions']), 0)

        self.env.ref('base.lang_fr').active = True
        self.user.lang = 'fr_FR'
        response = self.url_open(f'/spreadsheet/dashboard/data/{dashboard.id}')
        data = response.json()
        locale = data['snapshot']['settings']['locale']
        self.assertEqual(locale['code'], 'fr_FR')
        self.assertEqual(len(data['revisions']), 0)

    def test_load_with_company_currency(self):
        self.authenticate(self.user.login, self.user.password)
        dashboard = self.create_dashboard().with_user(self.user)
        response = self.url_open(f'/spreadsheet/dashboard/data/{dashboard.id}')
        data = response.json()
        self.assertEqual(
            data['default_currency'],
            self.env['res.currency'].get_company_currency_for_spreadsheet()
        )

    def test_load_with_selected_company_currency(self):
        usd, eur = self.env.ref('base.USD'), self.env.ref('base.EUR')
        usd_company = self.env['res.company'].create({'name': 'USD company', 'currency_id': usd.id})
        eur_company = self.env['res.company'].create({'name': 'EUR company', 'currency_id': eur.id})
        self.user.company_ids |= usd_company + eur_company
        self.user.company_id = usd_company
        self.authenticate(self.user.login, self.user.password)
        dashboard = self.create_dashboard().with_user(self.user)
        # the EUR company is selected in the company switcher
        self.opener.cookies.set('cids', f'{eur_company.id}-{usd_company.id}')
        response = self.url_open(f'/spreadsheet/dashboard/data/{dashboard.id}')
        self.assertEqual(
            response.json()['default_currency'],
            self.env['res.currency'].get_company_currency_for_spreadsheet(eur_company.id)
        )

    def test_translation_namespace(self):
        dashboard = self.create_dashboard()
        self.env['ir.model.data'].create({
            'name': 'test_translation_namespace',
            'module': 'spreadsheet_dashboard',
            'res_id': dashboard.id,
            'model': dashboard._name,
        })
        self.authenticate(self.user.login, self.user.password)
        response = self.url_open('/spreadsheet/dashboard/data/%s' % dashboard.id)
        data = response.json()
        self.assertEqual(data["translation_namespace"], "spreadsheet_dashboard")

    def test_get_sample_dashboard(self):
        self.authenticate(self.user.login, self.user.password)
        sample_dashboard_path = 'spreadsheet_dashboard/tests/data/sample_dashboard.json'
        dashboard = self.create_dashboard()
        dashboard.sample_dashboard_file_path = sample_dashboard_path
        dashboard.main_data_model_ids = [(4, self.env.ref('base.model_res_bank').id)]
        self.env['res.bank'].sudo().search([]).action_archive()
        response = self.url_open(f'/spreadsheet/dashboard/data/{dashboard.id}')
        self.assertEqual(response.json(), {
            'is_sample': True,
            'snapshot': {'sheets': []},
        })

    def test_load_dashboard_with_unreadable_main_model(self):
        self.authenticate(self.user.login, self.user.password)
        sample_dashboard_path = 'spreadsheet_dashboard/tests/data/sample_dashboard.json'
        dashboard = self.create_dashboard()
        dashboard.sample_dashboard_file_path = sample_dashboard_path
        dashboard.main_data_model_ids = [(4, self.env.ref('base.model_ir_model').id)]
        self.assertFalse(self.env['ir.model'].with_user(self.user).has_access('read'))

        response = self.url_open(f'/spreadsheet/dashboard/data/{dashboard.id}')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertNotIn('is_sample', data)
        self.assertEqual(data['revisions'], [])
