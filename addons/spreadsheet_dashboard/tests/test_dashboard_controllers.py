
from odoo import Command
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
        eur_company, usd_company = self.env['res.company'].create([
            {'name': 'Company with EUR', 'currency_id': self.env.ref('base.EUR').id},
            {'name': 'Company with USD', 'currency_id': self.env.ref('base.USD').id},
        ])
        self.user.write({
            'company_ids': [Command.set((eur_company + usd_company).ids)],
            'company_id': eur_company.id,
        })

        self.authenticate(self.user.login, self.user.password)
        dashboard = self.create_dashboard()
        url = f'/spreadsheet/dashboard/data/{dashboard.id}'

        # no active company selected: default company of the user
        data = self.url_open(url).json()
        self.assertEqual(data['default_currency']['code'], 'EUR')

        # active company selected in the company switcher
        data = self.url_open(url, cookies={'cids': f'{usd_company.id}-{eur_company.id}'}).json()
        self.assertEqual(data['default_currency']['code'], 'USD')

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
        dashboard.main_data_model_ids = [(4, self.env.ref('base.model_res_partner_bank').id)]
        self.env['res.partner.bank'].sudo().search([]).action_archive()
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
