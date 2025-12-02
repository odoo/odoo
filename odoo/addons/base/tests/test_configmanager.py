import os
import unittest
from unittest.mock import call, patch

import odoo
from odoo.tests import TransactionCase
from odoo.tools import file_open, file_open_temporary_directory, file_path
from odoo.tools.config import configmanager

EMPTY_CONFIG_PATH = file_path('base/tests/config/empty.conf')
PROJECT_PATH = odoo.tools.config.root_path.removesuffix('/odoo')
DEFAULT_DATADIR = odoo.tools.config._default_options['data_dir']

MISSING_HTTP_INTERFACE = """\
WARNING:odoo.tools.config:missing --http-interface/http_interface, \
using 0.0.0.0 by default, will change to 127.0.0.1 in 20.0"""


class TestConfigManager(TransactionCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        patcher = patch.dict('os.environ', {'ODOO_RC': EMPTY_CONFIG_PATH}, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.config = configmanager()

    def parse_reset(self, args=None):
        with (
            patch.dict(self.config._runtime_options, {}),
            patch.dict(self.config._cli_options, {}),
            patch.dict(self.config._env_options, {}),
            patch.dict(self.config._file_options, {}),
            patch.dict(self.config._default_options, {}),
        ):
            cli = self.config._parse_config(args)
            return cli, dict(self.config.options)

    def assertConfigEqual(self, truth):
        try:
            self.assertEqual(dict(self.config.options), truth)
        except AssertionError as exc1:
            for k in set(self.config.options).intersection(truth):
                try:
                    self.assertEqual(self.config.options[k], truth[k], f"{k!r} doesn't match")
                except AssertionError as exc2:
                    if hasattr(Exception, 'add_note'):  # 3.11
                        exc2.add_note(str(self.config._get_sources(k)))
                        raise exc2 from exc1
                    raise AssertionError(f"{exc2.args[0]}\n{self.config._get_sources(k)}") from exc1
            if missing := set(self.config.options).difference(truth):
                e = "missing from the test dict: " + ', '.join(missing)
                raise AssertionError(e) from exc1
            if missing := set(truth).difference(self.config.options):
                e = "missing from the configuration: " + ', '.join(missing)
                raise AssertionError(e) from exc1
            raise

    def test_00_setUp(self):
        self.assertEqual(self.config.options['config'], EMPTY_CONFIG_PATH)

    def test_01_default_config(self):
        self.assertConfigEqual({
            # options not exposed on the command line
            'admin_passwd': 'admin',
            'bin_path': '',
            'csv_internal_sep': ',',
            'default_productivity_apps': False,
            'proxy_access_token': '',
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'reportgz': False,
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': 0.2,
            'websocket_keep_alive_timeout': 3600,

            # common
            'config': EMPTY_CONFIG_PATH,
            'save': False,
            'init': {},
            'update': {},
            'reinit': [],
            'with_demo': False,
            'import_file_maxbytes': 10485760,
            'import_file_timeout': 3,
            'import_partial': '',
            'import_url_regex': '^(?:http|https)://',
            'pidfile': '',
            'addons_path': [],
            'upgrade_path': [],
            'pre_upgrade_scripts': [],
            'server_wide_modules': ['base', 'rpc', 'web'],
            'data_dir': DEFAULT_DATADIR,

            # HTTP
            'http_interface': '0.0.0.0',
            'http_port': 8069,
            'gevent_port': 8072,
            'http_enable': True,
            'proxy_mode': False,
            'x_sendfile': False,

            # web
            'dbfilter': '',

            # testing
            'test_file': '',
            'test_enable': False,
            'test_tags': None,
            'screencasts': '',
            'screenshots': '/tmp/odoo_tests',

            # logging
            'logfile': '',
            'syslog': False,
            'log_handler': [':INFO'],
            'log_db': '',
            'log_db_level': 'warning',
            'log_level': 'info',

            # SMTP
            'email_from': '',
            'from_filter': '',
            'smtp_server': 'localhost',
            'smtp_port': 25,
            'smtp_ssl': False,
            'smtp_user': '',
            'smtp_password': '',
            'smtp_ssl_certificate_filename': '',
            'smtp_ssl_private_key_filename': '',

            # database
            'db_name': [],
            'db_user': '',
            'db_password': '',
            'pg_path': '',
            'db_host': '',
            'db_port': None,
            'db_sslmode': 'prefer',
            'db_maxconn': 64,
            'db_maxconn_gevent': None,
            'db_template': 'template0',
            'db_replica_host': None,
            'db_replica_port': None,
            'db_app_name': 'odoo-{pid}',

            # i18n
            'load_language': None,
            'overwrite_existing_translations': False,
            # security
            'list_db': True,

            # advanced
            'dev_mode': [],
            'stop_after_init': False,
            'osv_memory_count_limit': 0,
            'transient_age_limit': 1.0,
            'max_cron_threads': 2,
            'limit_time_worker_cron': 0,
            'unaccent': False,
            'geoip_city_db': '/usr/share/GeoIP/GeoLite2-City.mmdb',
            'geoip_country_db': '/usr/share/GeoIP/GeoLite2-Country.mmdb',

            # multiprocessing
            'workers': 0,
            'limit_memory_soft': 2048 * 1024 * 1024,
            'limit_memory_soft_gevent': None,
            'limit_memory_hard': 2560 * 1024 * 1024,
            'limit_memory_hard_gevent': None,
            'limit_time_cpu': 60,
            'limit_time_real': 120,
            'limit_time_real_cron': -1,
            'limit_request': 2**16,
        })

    def test_02_config_file(self):
        config_path = file_path('base/tests/config/non_default.conf')
        with self.assertLogs('odoo.tools.config', 'WARNING') as capture:
            self.config._parse_config(['-c', config_path])
        self.assertConfigEqual({
            # options not exposed on the command line
            'admin_passwd': 'Tigrou007',
            'bin_path': '',
            'csv_internal_sep': '@',
            'default_productivity_apps': False,
            'proxy_access_token': '',
            'publisher_warranty_url': 'http://example.com',  # blacklist for save, read from the config file
            'reportgz': True,
            'websocket_rate_limit_burst': 1,
            'websocket_rate_limit_delay': 2.0,
            'websocket_keep_alive_timeout': 600,

            # common
            'config': config_path,
            'save': False,
            'init': {},  # blacklist for save, ignored from the config file
            'update': {},  # blacklist for save, ignored from the config file
            'reinit': [],
            'with_demo': True,
            'import_file_maxbytes': 10485760,
            'import_file_timeout': 3,
            'import_partial': '',
            'import_url_regex': '^(?:http|https)://',
            'pidfile': '/tmp/pidfile',
            'addons_path': [],  # the path found in the config file is invalid
            'upgrade_path': [],  # the path found in the config file is invalid
            'pre_upgrade_scripts': [],  # the path found in the config file is invalid
            'server_wide_modules': ['web', 'base', 'mail'],
            'data_dir': '/tmp/data-dir',

            # HTTP
            'http_interface': '10.0.0.254',
            'http_port': 6942,
            'gevent_port': 8012,
            'http_enable': False,
            'proxy_mode': True,
            'x_sendfile': True,

            # web
            'dbfilter': '.*',

            # testing
            'test_file': '',
            'test_enable': False,
            'test_tags': None,
            'screencasts': '/tmp/screencasts',
            'screenshots': '/tmp/screenshots',

            # logging
            'logfile': '/tmp/odoo.log',
            'syslog': False,
            'log_handler': [':DEBUG'],
            'log_db': 'logdb',
            'log_db_level': 'debug',
            'log_level': 'debug',

            # SMTP
            'email_from': 'admin@example.com',
            'from_filter': '.*',
            'smtp_server': 'smtp.localhost',
            'smtp_port': 1299,
            'smtp_ssl': True,
            'smtp_user': 'spongebob',
            'smtp_password': 'Tigrou0072',
            'smtp_ssl_certificate_filename': '/tmp/tlscert',
            'smtp_ssl_private_key_filename': '/tmp/tlskey',

            # database
            'db_name': ['horizon'],
            'db_user': 'kiwi',
            'db_password': 'Tigrou0073',
            'pg_path': '/tmp/pg_path',
            'db_host': 'db.localhost',
            'db_port': 4269,
            'db_sslmode': 'verify-full',
            'db_maxconn': 42,
            'db_maxconn_gevent': 100,
            'db_template': 'backup1706',
            'db_replica_host': 'db2.localhost',
            'db_replica_port': 2038,
            'db_app_name': 'odoo-{pid}',

            # i18n
            'load_language': 'fr_FR',  # blacklist for save, read from the config file
            'overwrite_existing_translations': False,  # blacklist for save, read from the config file

            # security
            'list_db': False,

            # advanced
            'dev_mode': ['xml'],  # blacklist for save, read from the config file
            'stop_after_init': False,
            'osv_memory_count_limit': 71,
            'transient_age_limit': 4.0,
            'max_cron_threads': 4,
            'limit_time_worker_cron': 600,
            'unaccent': True,
            'geoip_city_db': '/tmp/city.db',
            'geoip_country_db': '/tmp/country.db',

            # multiprocessing
            'workers': 92,
            'limit_memory_soft': 1048576,
            'limit_memory_soft_gevent': 1048577,
            'limit_memory_hard': 1048578,
            'limit_memory_hard_gevent': 1048579,
            'limit_time_cpu': 60,
            'limit_time_real': 61,
            'limit_time_real_cron': 62,
            'limit_request': 100,
        })
        self.assertEqual(capture.output, [
            "WARNING:odoo.tools.config:option addons_path, no such directory '/tmp/odoo', skipped",
            "WARNING:odoo.tools.config:option upgrade_path, no such directory '/tmp/upgrade', skipped",
            "WARNING:odoo.tools.config:option pre_upgrade_scripts, no such file '/tmp/pre-custom.py', skipped",
        ])

    @unittest.skipIf(os.name != 'posix', 'this test is POSIX only')
    def test_03_save_default_options(self):
        with file_open_temporary_directory(self.env) as temp_dir:
            config_path = f'{temp_dir}/save.conf'
            self.config._parse_config(['--config', config_path, '--save'])
            with (file_open(config_path, env=self.env) as config_file,
                  file_open('base/tests/config/save_posix.conf', env=self.env) as save_file):
                config_content = config_file.read().rstrip()
                save_content = save_file.read().format(
                    project_path=PROJECT_PATH,
                    homedir=self.config._normalize('~'),
                    empty_dict=r'{}',
                    pid='{pid}',
                )
                self.assertEqual(config_content.splitlines(), save_content.splitlines())

    def test_04_odoo16_config_file(self):
        # test that loading the Odoo 16.0 generated default config works
        # with a modern version
        config_path = file_path('base/tests/config/16.0.conf')
        with self.assertLogs('odoo.tools.config', 'WARNING') as capture:
            self.config._parse_config(['--config', config_path])
        with (
            self.assertNoLogs('py.warnings'),
            self.assertLogs('odoo.tools.config', 'WARNING') as capture_warn,
        ):
            self.config._warn_deprecated_options()
        self.assertConfigEqual({
            # options taken from the configuration file
            'admin_passwd': 'admin',
            'config': config_path,
            'csv_internal_sep': ',',
            'db_host': '',
            'db_maxconn': 64,
            'db_name': [],
            'db_password': '',
            'db_port': None,
            'db_sslmode': 'prefer',
            'db_template': 'template0',
            'db_user': '',
            'dbfilter': '',
            'demo': '{}',
            'email_from': '',
            'geoip_city_db': '/usr/share/GeoIP/GeoLite2-City.mmdb',
            'http_enable': True,
            'http_interface': '0.0.0.0',
            'http_port': 8069,
            'import_file_maxbytes': 10485760,
            'import_file_timeout': 3,
            'import_partial': '',
            'import_url_regex': '^(?:http|https)://',
            'list_db': True,
            'load_language': None,
            'log_db': '',
            'log_db_level': 'warning',
            'log_handler': [':INFO'],
            'log_level': 'info',
            'logfile': '',
            'max_cron_threads': 2,
            'limit_time_worker_cron': 0,
            'osv_memory_count_limit': 0,
            'overwrite_existing_translations': False,
            'pg_path': '',
            'pidfile': '',
            'proxy_mode': False,
            'reportgz': False,
            'screencasts': '',
            'screenshots': '/tmp/odoo_tests',
            'server_wide_modules': ['base', 'web'],
            'smtp_password': '',
            'smtp_port': 25,
            'smtp_server': 'localhost',
            'smtp_ssl': False,
            'smtp_user': '',
            'syslog': False,
            'test_enable': False,
            'test_file': '',
            'test_tags': None,
            'transient_age_limit': 1.0,
            'translate_modules': "['all']",
            'unaccent': False,
            'update': {},
            'reinit': [],
            'upgrade_path': [],
            'pre_upgrade_scripts': [],
            'with_demo': True,

            # options that are not taken from the file (also in 14.0)
            'addons_path': [],
            'data_dir': DEFAULT_DATADIR,
            'dev_mode': [],
            'geoip_database': '/usr/share/GeoIP/GeoLite2-City.mmdb',
            'init': {},
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'save': False,
            'stop_after_init': False,

            # undocummented options
            'bin_path': '',
            'default_productivity_apps': False,
            'osv_memory_age_limit': 'False',
            'proxy_access_token': '',

            # multiprocessing
            'workers': 0,
            'limit_memory_soft': 2048 * 1024 * 1024,
            'limit_memory_soft_gevent': None,
            'limit_memory_hard': 2560 * 1024 * 1024,
            'limit_memory_hard_gevent': None,
            'limit_time_cpu': 60,
            'limit_time_real': 120,
            'limit_time_real_cron': -1,
            'limit_request': 1 << 16,

            # new options since 14.0
            'db_maxconn_gevent': None,
            'db_replica_host': None,
            'db_replica_port': None,
            'db_app_name': 'odoo-{pid}',
            'geoip_country_db': '/usr/share/GeoIP/GeoLite2-Country.mmdb',
            'from_filter': '',
            'gevent_port': 8072,
            'smtp_ssl_certificate_filename': '',
            'smtp_ssl_private_key_filename': '',
            'websocket_keep_alive_timeout': 3600,
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': 0.2,
            'x_sendfile': False,
        })

        def missing(*options):
            return [
                f"WARNING:odoo.tools.config:unknown option '{option}' in "
                f"the config file at {config_path}, option stored as-is, "
                "without parsing"
                for option in options
            ]

        def falsy(*options):
            return [
                f"WARNING:odoo.tools.config:option {option} reads 'False' "
                f"in the config file at {config_path} but isn't a boolean "
                "option, skip"
                for option in options
            ]

        self.assertEqual(capture.output,
            missing('demo', 'geoip_database', 'osv_memory_age_limit')
            + falsy(
                'db_host', 'db_name', 'db_password', 'db_port',
                'db_user', 'email_from', 'from_filter', 'log_db',
                'smtp_password', 'smtp_ssl_certificate_filename',
                'smtp_ssl_private_key_filename', 'smtp_user',
            )
            + missing('translate_modules'),
        )
        self.assertEqual(capture_warn.output, [
            'WARNING:odoo.tools.config:missing --http-interface/http_interface, '
               'using 0.0.0.0 by default, will change to 127.0.0.1 in 20.0',
        ])

    def test_05_repeat_parse_config(self):
        """Emulate multiple calls to parse_config()"""
        with self.assertLogs('odoo.tools.config', 'WARNING') as capture:
            config = configmanager()
            config._parse_config()
            config._warn_deprecated_options()
            config._parse_config()
            config._warn_deprecated_options()
        self.assertEqual(capture.output, [MISSING_HTTP_INTERFACE] * 2)

    def test_06_cli(self):
        with file_open('base/tests/config/cli') as file:
            with self.assertLogs('odoo.tools.config', 'WARNING') as capture:
                self.config._parse_config(file.read().split())
        self.assertEqual(capture.output, [
            "WARNING:odoo.tools.config:test file '/tmp/file-file' cannot be found",
        ])

        self.assertConfigEqual({
            # options not exposed on the command line
            'admin_passwd': 'admin',
            'bin_path': '',
            'csv_internal_sep': ',',
            'default_productivity_apps': False,
            'proxy_access_token': '',
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'reportgz': False,
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': .2,
            'websocket_keep_alive_timeout': 3600,

            # common
            'config': EMPTY_CONFIG_PATH,
            'save': False,
            'init': {'hr': True, 'stock': True},
            'update': {'account': True, 'website': True},
            'reinit': ['account'],
            'with_demo': True,
            'import_file_maxbytes': 10485760,
            'import_file_timeout': 3,
            'import_partial': '/tmp/import-partial',
            'import_url_regex': '^(?:http|https)://',
            'pidfile': '/tmp/pidfile',
            'addons_path': [],
            'upgrade_path': [],
            'pre_upgrade_scripts': [],
            'server_wide_modules': ['web', 'base', 'mail'],
            'data_dir': '/tmp/data-dir',

            # HTTP
            'http_interface': '10.0.0.254',
            'http_port': 6942,
            'gevent_port': 8012,
            'http_enable': False,
            'proxy_mode': True,
            'x_sendfile': True,

            # web
            'dbfilter': '.*',

            # testing
            'test_file': '/tmp/file-file',
            'test_enable': True,
            'test_tags': ':TestMantra.test_is_extra_mile_done',
            'screencasts': '/tmp/screencasts',
            'screenshots': '/tmp/screenshots',

            # logging
            'logfile': '/tmp/odoo.log',
            'syslog': False,
            'log_handler': [
                ':WARNING',
                'odoo.tools.config:DEBUG',
                'odoo.http:DEBUG',
                'odoo.sql_db:DEBUG',
            ],
            'log_db': 'logdb',
            'log_db_level': 'debug',
            'log_level': 'debug',

            # SMTP
            'email_from': 'admin@example.com',
            'from_filter': '.*',
            'smtp_server': 'smtp.localhost',
            'smtp_port': 1299,
            'smtp_ssl': True,
            'smtp_user': 'spongebob',
            'smtp_password': 'Tigrou0072',
            'smtp_ssl_certificate_filename': '/tmp/tlscert',
            'smtp_ssl_private_key_filename': '/tmp/tlskey',

            # database
            'db_name': ['horizon'],
            'db_user': 'kiwi',
            'db_password': 'Tigrou0073',
            'pg_path': '/tmp/pg_path',
            'db_host': 'db.localhost',
            'db_port': 4269,
            'db_sslmode': 'verify-full',
            'db_maxconn': 42,
            'db_maxconn_gevent': 100,
            'db_template': 'backup1706',
            'db_replica_host': 'db2.localhost',
            'db_replica_port': 2038,
            'db_app_name': 'myapp{pid}',

            # i18n
            'load_language': 'fr_FR',
            'overwrite_existing_translations': True,
            # security
            'list_db': False,

            # advanced
            'dev_mode': ['xml', 'reload'],
            'stop_after_init': True,
            'osv_memory_count_limit': 71,
            'transient_age_limit': 4.0,
            'max_cron_threads': 4,
            'limit_time_worker_cron': 0,
            'unaccent': True,
            'geoip_city_db': '/tmp/city.db',
            'geoip_country_db': '/tmp/country.db',

            'workers': 92,
            'limit_memory_soft': 1048576,
            'limit_memory_soft_gevent': 1048577,
            'limit_memory_hard': 1048578,
            'limit_memory_hard_gevent': 1048579,
            'limit_time_cpu': 60,
            'limit_time_real': 61,
            'limit_time_real_cron': 62,
            'limit_request': 100,
        })

    def test_07_environ(self):
        with file_open('base/tests/config/environ') as file:
            os.environ.update({
                x[0]: x[2]
                for line in file.readlines()
                if (x := line.rstrip('\n').partition('=')) and x[0]
                and not line.startswith('#')
            })
        self.config._parse_config()

        self.assertConfigEqual({
            # options not exposed on the command line
            'admin_passwd': 'admin',
            'bin_path': '',
            'csv_internal_sep': ',',
            'default_productivity_apps': False,
            'proxy_access_token': '',
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'reportgz': False,
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': .2,
            'websocket_keep_alive_timeout': 3600,

            # common
            'config': EMPTY_CONFIG_PATH,
            'save': False,
            'init': {},
            'update': {},
            'reinit': [],
            'with_demo': True,
            'import_file_maxbytes': 10485760,
            'import_file_timeout': 3,
            'import_partial': '',
            'import_url_regex': '^(?:http|https)://',
            'pidfile': '/tmp/pidfile',
            'addons_path': [],
            'upgrade_path': [],
            'pre_upgrade_scripts': [],
            'server_wide_modules': ['web', 'base', 'mail'],
            'data_dir': '/tmp/data-dir',

            # HTTP
            'http_interface': '10.0.0.254',
            'http_port': 6942,
            'gevent_port': 8012,
            'http_enable': False,
            'proxy_mode': True,
            'x_sendfile': True,

            # web
            'dbfilter': '.*',

            # testing
            'test_file': '',
            'test_enable': False,
            'test_tags': None,
            'screencasts': '/tmp/screencasts',
            'screenshots': '/tmp/screenshots',

            # logging
            'logfile': '/tmp/odoo.log',
            'syslog': False,
            'log_handler': [
                ':WARNING',
                'odoo.tools.config:DEBUG',
            ],
            'log_db': 'logdb',
            'log_db_level': 'debug',
            'log_level': 'debug',

            # SMTP
            'email_from': 'admin@example.com',
            'from_filter': '.*',
            'smtp_server': 'smtp.localhost',
            'smtp_port': 1299,
            'smtp_ssl': True,
            'smtp_user': 'spongebob',
            'smtp_password': 'Tigrou0072',
            'smtp_ssl_certificate_filename': '/tmp/tlscert',
            'smtp_ssl_private_key_filename': '/tmp/tlskey',

            # database
            'db_name': ['horizon'],
            'db_user': 'kiwi',
            'db_password': 'Tigrou0073',
            'pg_path': '/tmp/pg_path',
            'db_host': 'db.localhost',
            'db_port': 4269,
            'db_sslmode': 'verify-full',
            'db_maxconn': 42,
            'db_maxconn_gevent': 100,
            'db_template': 'backup1706',
            'db_replica_host': 'db2.localhost',
            'db_replica_port': 2038,
            'db_app_name': 'envapp',

            # i18n (not loaded)
            'load_language': None,
            'overwrite_existing_translations': False,

            # security
            'list_db': False,

            # advanced
            'dev_mode': ['xml', 'reload'],
            'stop_after_init': False,  # not on env
            'osv_memory_count_limit': 71,
            'transient_age_limit': 4.0,
            'max_cron_threads': 4,
            'limit_time_worker_cron': 0,
            'unaccent': True,
            'geoip_city_db': '/tmp/city.db',
            'geoip_country_db': '/tmp/country.db',

            'workers': 92,
            'limit_memory_soft': 1048576,
            'limit_memory_soft_gevent': 1048577,
            'limit_memory_hard': 1048578,
            'limit_memory_hard_gevent': 1048579,
            'limit_time_cpu': 60,
            'limit_time_real': 61,
            'limit_time_real_cron': 62,
            'limit_request': 100,
        })

    @patch('optparse.OptionParser.error')
    def test_06_syslog_logfile_exclusive_cli(self, error):
        self.parse_reset(['--syslog', '--logfile', 'logfile'])
        self.parse_reset(['-c', file_path('base/tests/config/sysloglogfile.conf')])
        error.assert_has_calls(2 * [call("the syslog and logfile options are exclusive")])

    @patch('optparse.OptionParser.error')
    def test_10_init_update_incompatible_with_multidb(self, error):
        self.parse_reset(['-d', 'db1,db2', '-i', 'base'])
        self.parse_reset(['-d', 'db1,db2', '-u', 'base'])
        self.parse_reset(['-c', file_path('base/tests/config/multidb.conf'), '-i', 'base'])
        self.parse_reset(['-c', file_path('base/tests/config/multidb.conf'), '-u', 'base'])
        error.assert_has_calls(4 * [call("Cannot use -i/--init or -u/--update with multiple databases in the -d/--database/db_name")])

    def test_11_auto_stop_after_init_after_test(self):
        for args, stop_after_init in [
            ([], False),
            (['--stop'], True),
            (['--test-enable'], True),
            (['--test-tags', 'tag'], True),
            (['--test-file', __file__], True),
        ]:
            with self.subTest(args=args):
                if any('--test' in arg for arg in args):
                    with self.assertLogs('odoo.tools.config', 'WARNING') as capture:
                        _, options = self.parse_reset(args)
                    self.assertEqual(capture.output, [
                        "WARNING:odoo.tools.config:Empty -d/--database/db_name, tests won't run",
                    ])
                else:
                    _, options = self.parse_reset(args)
                self.assertEqual(options['stop_after_init'], stop_after_init)

    def test_13_empty_db_replica_host(self):
        with self.assertLogs('py.warnings', 'WARNING') as capture:
            _, options = self.parse_reset(['--db_replica_host', ''])
        self.assertIsNone(options['db_replica_host'])
        self.assertEqual(options['dev_mode'], ['replica'])
        self.assertEqual(len(capture.output), 1)
        self.assertIn('Since 19.0, an empty --db_replica_host', capture.output[0])

        with self.assertNoLogs('py.warnings', 'WARNING'):
            _, options = self.parse_reset(['--db_replica_host', '', '--dev', 'replica'])
        self.assertIsNone(options['db_replica_host'])
        self.assertEqual(options['dev_mode'], ['replica'])
