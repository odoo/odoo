
from http import HTTPStatus
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

    def test_dashboard_etag(self):
        self.authenticate(self.user.login, self.user.password)
        self.user.lang = 'en_US'
        dashboard = self.create_dashboard()

        # First request
        response = self.url_open(
            '/spreadsheet/dashboard/data/%s' % dashboard.id)
        response.raise_for_status()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        etag = response.headers.get('ETag')
        self.assertIsNotNone(etag)

        # Second request with If-None-Match header
        response = self.url_open(
            '/spreadsheet/dashboard/data/%s' % dashboard.id,
            headers={'If-None-Match': etag},
        )
        response.raise_for_status()
        self.assertEqual(response.status_code, HTTPStatus.NOT_MODIFIED)

        # Third request with If-None-Match header with weak ETag
        weak_etag = 'W/' + etag
        response = self.url_open(
            '/spreadsheet/dashboard/data/%s' % dashboard.id,
            headers={'If-None-Match': weak_etag},
        )
        response.raise_for_status()
        self.assertEqual(response.status_code, HTTPStatus.NOT_MODIFIED)

        # Modify the user locale
        self.env.ref('base.lang_fr').active = True
        self.user.lang = 'fr_FR'

        # Fourth request with old ETag
        response = self.url_open(
            '/spreadsheet/dashboard/data/%s' % dashboard.id,
            headers={'If-None-Match': etag},
        )
        response.raise_for_status()
        self.assertEqual(response.status_code, HTTPStatus.OK)
        new_etag = response.headers.get('ETag')
        self.assertIsNotNone(new_etag)
        self.assertNotEqual(etag, new_etag)
