from datetime import timedelta
from unittest.mock import MagicMock

from psycopg2 import OperationalError

from odoo import fields, release
from odoo.addons.base_setup.controllers import kpi as kpi_controller
from odoo.tests import HttpCase, new_test_user, patch, tagged, TransactionCase


@tagged('post_install', '-at_install')
class KpiTest(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.kpi_user = new_test_user(cls.env, 'kpi_user@domain.tld')
        cls.kpi_user_api_key = cls.env['res.users.apikeys'].with_user(cls.kpi_user)._generate(
            scope='rpc', name='test', expiration_date=fields.Datetime.now() + timedelta(days=0.5))

        # Make db_connect return the current cursor, so that it sees the prepared transaction without needing a commit
        cls.startClassPatcher(patch('odoo.addons.base_setup.controllers.kpi.db_connect',
                                    **{'return_value.cursor.return_value.__enter__.return_value': cls.env.cr}))

    def setUp(self):
        super().setUp()

        # Mock the KPI providers with the test's ones
        self.mock_kpi_providers = self.startClassPatcher(patch('odoo.addons.base_setup.controllers.kpi._get_kpi_providers',
                                                               return_value=[]))

    def _make_json_request(self, url, json=None):
        response = self.url_open(url, json=json)
        response.raise_for_status()
        result = response.json()
        if 'error' in result:
            data = result['error']['data']
            self.fail("JSON request encountered an error:\n"
                      f"{data['name']}: {data['message']}\n"
                      f"{data['debug']}")
        return result['result']

    def test_get_kpi_summary(self):
        self.mock_kpi_providers.return_value = [
            ('some_module', ':kpi_provider_hook', lambda cr, uid: ['some_module result 1', 'some_module result 2']),
            ('another_module', ':get_kpi_summary', lambda cr, uid: ['another_module result 1', 'another_module result 2']),
        ]

        params = {
            'credentials': [[self.env.cr.dbname, self.kpi_user_api_key]],
        }
        result = self._make_json_request('/kpi/summary', json={'params': params})

        self.assertEqual([*result], [self.env.cr.dbname])
        db_result = result[self.env.cr.dbname]

        self.assertCountEqual([*db_result], ['database_version', 'users', 'kpi_summary', 'errors'])
        self.assertEqual(db_result['errors'], [])
        self.assertEqual(db_result['database_version'], release.series)
        self.assertCountEqual(db_result['kpi_summary'], [
            'another_module result 1',
            'another_module result 2',
            'some_module result 1',
            'some_module result 2',
        ])
        # search_read would be ideal, but we need to convert the date to string
        expected_users = [{
            'id': u.id,
            'name': u.name,
            'login': u.login,
            'login_date': fields.Datetime.to_string(u.login_date) if u.login_date else None,
        } for u in self.env['res.users'].search([('share', '=', False)])]
        self.assertCountEqual(db_result['users'], expected_users)

    def test_get_kpi_summary_on_nonexistant_database(self):
        # Avoid leaking information about missing database to prevent scanning databases hosted on the same server
        self.startPatcher(patch('odoo.addons.base_setup.controllers.kpi.db_connect', side_effect=OperationalError))

        params = {
            'credentials': [['missing-database', 'any_token']],
        }
        with self.assertNoLogs('odoo.addons.base_setup.controllers.kpi', level='ERROR'):
            result = self._make_json_request('/kpi/summary', json={'params': params})
        self.assertEqual(result, {}, "The route shouldn't leak information about database existence")

    def test_get_kpi_summary_with_invalid_credential(self):
        params = {
            'credentials': [[self.env.cr.dbname, 'invalid_token']],
        }
        with self.assertLogs('odoo.addons.base_setup.controllers.kpi', level='ERROR') as log_catcher:
            result = self._make_json_request('/kpi/summary', json={'params': params})
        self.assertEqual(result, {}, "The route should behave as if the database does not exist")
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn(f"invalid api key for database {self.env.cr.dbname!r}", log_catcher.output[0])

    def test_get_kpi_summary_with_version_mismatch(self):
        # If a database is listed but has a version that doesn't match the current release, ignore the database

        # It would be wrong to try to run the SQL queries on a different version, as the model and meaning of fields may change.
        # We can't check the API key validity on a different version, as we don't want to freeze the res.users.apikeys model.
        # Having an error message would reveal the existence of the database even if we have no access
        # Therefore the best solution is to behave as if this server doesn't know about this database,
        # and let the client try to retrieve the KPI summary via dedicated RPC calls.
        self.startPatcher(patch('odoo.addons.base_setup.controllers.kpi.release_series', new='saas~9.11'))

        params = {
            'credentials': [[self.env.cr.dbname, self.kpi_user_api_key]],
        }
        with self.assertLogs('odoo.addons.base_setup.controllers.kpi', level='ERROR') as log_catcher:
            result = self._make_json_request('/kpi/summary', json={'params': params})
        self.assertEqual(result, {}, "The route should behave as if the databases does not exist")
        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn(f"database {self.env.cr.dbname!r} has version {self.env['ir.module.module']._get('base').latest_version!r} "
                      "that doesn't match running version 'saas~9.11'", log_catcher.output[0])

    def test_get_kpi_summary_limits_credentials_count(self):
        credentials = [['some-db', 'some_token']] * 501
        params = {'credentials': credentials}
        with self.assertLogs('odoo.http', 'WARNING') as log_catcher:
            response = self.url_open('/kpi/summary', json={'params': params})
        response.raise_for_status()
        result = response.json()
        self.assertEqual(result['error']['data']['message'], 'Too many credentials')
        self.assertIn('Too many credentials', log_catcher.output[0])

    def test_get_kpi_summary_partial_provider_failure(self):
        def failing_provider(cr, uid):
            raise RuntimeError("boom")

        self.mock_kpi_providers.return_value = [
            ('working_module', ':working_provider', lambda cr, uid: ['working result']),
            ('broken_module', 'pkg.module:broken_provider', failing_provider),
            ('another_working_module', 'pkg.module:another_provider', lambda cr, uid: ['another result']),
        ]

        params = {
            'credentials': [[self.env.cr.dbname, self.kpi_user_api_key]],
        }

        with self.assertLogs('odoo.addons.base_setup.controllers.kpi', level='ERROR') as log_catcher:
            result = self._make_json_request('/kpi/summary', json={'params': params})

        db_result = result[self.env.cr.dbname]

        self.assertCountEqual(db_result['kpi_summary'], [
            'working result',
            'another result',
        ])

        self.assertEqual(db_result['errors'], [{
            'addon': 'broken_module',
            'kpi_provider': 'pkg.module:broken_provider',
            'message': "get_kpi_summary error in addon 'broken_module', provider 'pkg.module:broken_provider'",
        }])

        self.assertEqual(len(log_catcher.output), 1)
        self.assertIn(
            "get_kpi_summary error in addon 'broken_module', provider 'pkg.module:broken_provider'",
            log_catcher.output[0],
        )


@tagged('-at_install', 'post_install')
class TestKpiProviderLoading(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        fake_manifest = MagicMock()
        fake_manifest.name = "test_addon"
        fake_manifest.get.return_value = [
            "sub.module:func",
            ":root_func",
            "invalidformat",
            "module.only:",
            ".bad:func",
        ]

        fake_module = MagicMock()
        fake_module.__name__ = "odoo.addons.test_addon.sub.module"
        fake_module.func = lambda: None
        fake_module.root_func = lambda: None

        def fake_import(name, package=None):
            return fake_module

        fake_root_module = MagicMock()
        fake_root_module.__name__ = "odoo.addons.test_addon"

        def fake_import_root(name, package=None):
            return fake_root_module

        cls.startClassPatcher(patch.object(
            kpi_controller.Manifest,
            "all_addon_manifests",
            return_value=[fake_manifest],
        ))
        cls.import_mock = cls.startClassPatcher(patch.object(
            kpi_controller,
            "import_module",
            side_effect=lambda name, package=None: fake_module if "sub" in name else fake_root_module,
        ))

    def test_get_kpi_providers_parsing_and_filtering(self):
        with self.assertLogs('odoo.addons.base_setup.controllers.kpi', level='WARNING') as log_catcher:
            result = kpi_controller._get_kpi_providers()

        # Only valid entries should survive
        self.assertEqual(len(result), 2)

        addons = [r[0] for r in result]
        providers = [r[1] for r in result]

        self.assertEqual(addons, ["test_addon", "test_addon"])

        # normalized format check
        self.assertIn("sub.module:func", providers)
        self.assertIn(":root_func", providers)

        self.assertEqual(len(log_catcher.output), 3)
        self.assertIn("Invalid KPI provider hook path 'invalidformat' in addon 'test_addon'.", log_catcher.output[0])
        self.assertIn("KPI provider 'module.only:' from addon 'test_addon' has an empty function name.", log_catcher.output[1])
        self.assertIn("Invalid KPI provider hook path '.bad:func' in addon 'test_addon'.", log_catcher.output[2])
