
from odoo.tests.common import HttpCase

from .common import DashboardTestCommon


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
