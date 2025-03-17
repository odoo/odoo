import unittest

import odoo
from odoo.tests import TransactionCase
from odoo.tools import file_path, file_open, file_open_temporary_directory
from odoo.tools.config import conf, configmanager, _get_default_datadir


IS_POSIX = 'workers' in odoo.tools.config.options
ROOT_PATH = odoo.tools.config.options['root_path'].removesuffix('/odoo')


class TestConfigManager(TransactionCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        # _parse_config() as the side-effect of changing those two
        # values, make sure the original value is restored at the end.
        self.patch(conf, 'addons_paths', odoo.conf.addons_paths)
        self.patch(conf, 'server_wide_modules', odoo.conf.server_wide_modules)

    def test_01_default_config(self):
        config = configmanager(fname=file_path('base/tests/config/empty.conf'))

        default_values = {
            # options not exposed on the command line
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'reportgz': False,
            'root_path': f'{ROOT_PATH}/odoo',
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': 0.2,
            'websocket_keep_alive_timeout': 3600,

            # common
            'config': None,
            'save': None,
            'init': {},
            'update': {},
            'without_demo': False,
            'demo': {},
            'import_partial': '',
            'pidfile': '',
            'addons_path': f'{ROOT_PATH}/odoo/addons,{ROOT_PATH}/addons',
            'upgrade_path': '',
            'server_wide_modules': 'base,web',
            'data_dir': _get_default_datadir(),

            # HTTP
            'http_interface': '',
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
            'log_db': False,
            'log_db_level': 'warning',
            'log_level': 'info',

            # SMTP
            'email_from': False,
            'from_filter': False,
            'smtp_server': 'localhost',
            'smtp_port': 25,
            'smtp_ssl': False,
            'smtp_user': False,
            'smtp_password': False,
            'smtp_ssl_certificate_filename': False,
            'smtp_ssl_private_key_filename': False,

            # database
            'db_name': False,
            'db_user': False,
            'db_password': False,
            'pg_path': '',
            'db_host': False,
            'db_port': False,
            'db_sslmode': 'prefer',
            'db_maxconn': 64,
            'db_maxconn_gevent': False,
            'db_template': 'template0',
            'db_replica_host': False,
            'db_replica_port': False,

            # i18n
            'load_language': None,
            'language': None,
            'translate_out': '',
            'translate_in': '',
            'overwrite_existing_translations': False,
            'translate_modules': ['all'],

            # security
            'list_db': True,

            # advanced
            'dev_mode': [],
            'shell_interface': None,
            'stop_after_init': False,
            'osv_memory_count_limit': 0,
            'transient_age_limit': 1.0,
            'max_cron_threads': 2,
            'limit_time_worker_cron': 0,
            'unaccent': False,
            'geoip_city_db': '/usr/share/GeoIP/GeoLite2-City.mmdb',
            'geoip_country_db': '/usr/share/GeoIP/GeoLite2-Country.mmdb',
        }

        if IS_POSIX:
            # multiprocessing
            default_values.update(
                {
                    'workers': 0,
                    'limit_memory_soft': 2048 * 1024 * 1024,
                    'limit_memory_soft_gevent': False,
                    'limit_memory_hard': 2560 * 1024 * 1024,
                    'limit_memory_hard_gevent': False,
                    'limit_time_cpu': 60,
                    'limit_time_real': 120,
                    'limit_time_real_cron': -1,
                    'limit_request': 2**16,
                }
            )

        config._parse_config()
        self.assertEqual(config.options, default_values, "Options don't match")

    def test_02_config_file(self):
        values = {
            # options not exposed on the command line
            'admin_passwd': 'Tigrou007',
            'csv_internal_sep': '@',
            'publisher_warranty_url': 'http://example.com',  # blacklist for save, read from the config file
            'reportgz': True,
            'root_path': f'{ROOT_PATH}/odoo',  # blacklist for save, ignored from the config file
            'websocket_rate_limit_burst': '1',
            'websocket_rate_limit_delay': '2',
            'websocket_keep_alive_timeout': '600',

            # common
            'config': '/tmp/config',  # blacklist for save, read from the config file
            'save': True,  # blacklist for save, read from the config file
            'init': {},  # blacklist for save, ignored from the config file
            'update': {},  # blacklist for save, ignored from the config file
            'without_demo': True,
            'demo': {},  # blacklist for save, ignored from the config file
            'import_partial': '/tmp/import-partial',
            'pidfile': '/tmp/pidfile',
            'addons_path': '/tmp/odoo',
            'upgrade_path': '/tmp/upgrade',
            'server_wide_modules': 'base,mail',
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
            'db_name': 'horizon',
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

            # i18n
            'load_language': 'fr_FR',  # blacklist for save, read from the config file
            'language': 'fr_FR',  # blacklist for save, read from the config file
            'translate_out': '/tmp/translate_out.csv',  # blacklist for save, read from the config file
            'translate_in': '/tmp/translate_in.csv',  # blacklist for save, read from the config file
            'overwrite_existing_translations': True,  # blacklist for save, read from the config file
            'translate_modules': ['all'],  # ignored from the config file

            # security
            'list_db': False,

            # advanced
            'dev_mode': [],  # blacklist for save, ignored from the config file
            'shell_interface': 'ipython',  # blacklist for save, read from the config file
            'stop_after_init': True,  # blacklist for save, read from the config file
            'osv_memory_count_limit': 71,
            'transient_age_limit': 4.0,
            'max_cron_threads': 4,
            'limit_time_worker_cron': 600,
            'unaccent': True,
            'geoip_city_db': '/tmp/city.db',
            'geoip_country_db': '/tmp/country.db',
        }

        if IS_POSIX:
            # multiprocessing
            values.update(
                {
                    'workers': 92,
                    'limit_memory_soft': 1048576,
                    'limit_memory_soft_gevent': 1048577,
                    'limit_memory_hard': 1048578,
                    'limit_memory_hard_gevent': 1048579,
                    'limit_time_cpu': 60,
                    'limit_time_real': 61,
                    'limit_time_real_cron': 62,
                    'limit_request': 100,
                }
            )

        config_path = file_path('base/tests/config/non_default.conf')
        config = configmanager(fname=config_path)
        self.assertEqual(config.rcfile, config_path, "Config file path doesn't match")

        config._parse_config()
        self.assertEqual(config.options, values, "Options don't match")
        self.assertEqual(config.rcfile, config_path)
        self.assertNotEqual(config.rcfile, config['config'])  # funny

    @unittest.skipIf(not IS_POSIX, 'this test is POSIX only')
    def test_03_save_default_options(self):
        with file_open_temporary_directory(self.env) as temp_dir:
            config_path = f'{temp_dir}/save.conf'
            config = configmanager(fname=config_path)
            config._parse_config(['--config', config_path, '--save'])
            with (file_open(config_path, env=self.env) as config_file,
                  file_open('base/tests/config/save_posix.conf', env=self.env) as save_file):
                config_content = config_file.read().rstrip()
                save_content = save_file.read().format(
                    root_path=ROOT_PATH,
                    homedir=config._normalize('~'),
                    empty_dict=r'{}',
                )
                self.assertEqual(config_content.splitlines(), save_content.splitlines())

    def test_04_odoo16_config_file(self):
        # test that loading the Odoo 16.0 generated default config works
        # with a modern version
        config = configmanager(fname=file_path('base/tests/config/16.0.conf'))

        assert_options = {
            # options taken from the configuration file
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'db_host': False,
            'db_maxconn': 64,
            'db_name': False,
            'db_password': False,
            'db_port': False,
            'db_sslmode': 'prefer',
            'db_template': 'template0',
            'db_user': False,
            'dbfilter': '',
            'demo': {},
            'email_from': False,
            'geoip_city_db': '/usr/share/GeoIP/GeoLite2-City.mmdb',
            'http_enable': True,
            'http_interface': '',
            'http_port': 8069,
            'import_partial': '',
            'list_db': True,
            'load_language': None,
            'log_db': False,
            'log_db_level': 'warning',
            'log_handler': [':INFO'],
            'log_level': 'info',
            'logfile': '',
            'max_cron_threads': 2,
            'osv_memory_count_limit': 0,
            'overwrite_existing_translations': False,
            'pg_path': '',
            'pidfile': '',
            'proxy_mode': False,
            'reportgz': False,
            'screencasts': '',
            'screenshots': '/tmp/odoo_tests',
            'server_wide_modules': 'base,web',
            'smtp_password': False,
            'smtp_port': 25,
            'smtp_server': 'localhost',
            'smtp_ssl': False,
            'smtp_user': False,
            'syslog': False,
            'test_enable': False,
            'test_file': '',
            'test_tags': None,
            'transient_age_limit': 1.0,
            'translate_modules': ['all'],
            'unaccent': False,
            'update': {},
            'upgrade_path': '',
            'without_demo': False,

            # options that are not taken from the file (also in 14.0)
            'addons_path': f'{ROOT_PATH}/odoo/addons,{ROOT_PATH}/addons',
            'config': None,
            'data_dir': _get_default_datadir(),
            'dev_mode': [],
            'init': {},
            'language': None,
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'save': None,
            'shell_interface': None,
            'stop_after_init': False,
            'root_path': f'{ROOT_PATH}/odoo',
            'translate_in': '',
            'translate_out': '',

            # new options since 14.0
            'db_maxconn_gevent': False,
            'db_replica_host': False,
            'db_replica_port': False,
            'geoip_country_db': '/usr/share/GeoIP/GeoLite2-Country.mmdb',
            'from_filter': False,
            'gevent_port': 8072,
            'smtp_ssl_certificate_filename': False,
            'smtp_ssl_private_key_filename': False,
            'websocket_keep_alive_timeout': '3600',
            'websocket_rate_limit_burst': '10',
            'websocket_rate_limit_delay': '0.2',
            'x_sendfile': False,
            'limit_time_worker_cron': 0,
        }
        if IS_POSIX:
            # multiprocessing
            assert_options.update(
                {
                    'workers': 0,
                    'limit_memory_soft': 2048 * 1024 * 1024,
                    'limit_memory_soft_gevent': False,
                    'limit_memory_hard': 2560 * 1024 * 1024,
                    'limit_memory_hard_gevent': False,
                    'limit_time_cpu': 60,
                    'limit_time_real': 120,
                    'limit_time_real_cron': -1,
                    'limit_request': 1 << 16,
                }
            )

        config._parse_config()
        with self.assertNoLogs('py.warnings'):
            config._warn_deprecated_options()
        self.assertEqual(config.options, assert_options, "Options don't match")

    def test_05_repeat_parse_config(self):
        """Emulate multiple calls to parse_config()"""
        config = configmanager()
        config._parse_config()
        config._warn_deprecated_options()
        config._parse_config()
        config._warn_deprecated_options()

    def test_06_cli(self):
        config = configmanager(fname=file_path('base/tests/config/empty.conf'))
        with file_open('base/tests/config/cli') as file:
            config._parse_config(file.read().split())

        values = {
            # options not exposed on the command line
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'publisher_warranty_url': 'http://services.odoo.com/publisher-warranty/',
            'reportgz': False,
            'root_path': f'{ROOT_PATH}/odoo',
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': .2,
            'websocket_keep_alive_timeout': 3600,

            # common
            'config': None,
            'save': None,
            'init': {'hr': 1, 'stock': 1},
            'update': {'account': 1, 'website': 1},
            'without_demo': 'rigolo',
            'demo': {},
            'import_partial': '/tmp/import-partial',
            'pidfile': '/tmp/pidfile',
            'addons_path': f'{ROOT_PATH}/odoo/addons,{ROOT_PATH}/addons',
            'upgrade_path': '',
            'server_wide_modules': 'base,mail',
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
                ':INFO',
                'odoo.tools.config:DEBUG',
                ':WARNING',
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
            'db_name': 'horizon',
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

            # i18n
            'load_language': 'fr_FR',
            'language': 'fr_FR',
            'translate_out': '/tmp/translate_out.csv',
            'translate_in': '/tmp/translate_in.csv',
            'overwrite_existing_translations': True,
            'translate_modules': ['hr', 'mail', 'stock'],

            # security
            'list_db': False,

            # advanced
            'dev_mode': ['xml', 'reload'],
            'shell_interface': 'ipython',
            'stop_after_init': True,
            'osv_memory_count_limit': 71,
            'transient_age_limit': 4.0,
            'max_cron_threads': 4,
            'limit_time_worker_cron': 0,
            'unaccent': True,
            'geoip_city_db': '/tmp/city.db',
            'geoip_country_db': '/tmp/country.db',
        }

        if IS_POSIX:
            # multiprocessing
            values.update(
                {
                    'workers': 92,
                    'limit_memory_soft': 1048576,
                    'limit_memory_soft_gevent': 1048577,
                    'limit_memory_hard': 1048578,
                    'limit_memory_hard_gevent': 1048579,
                    'limit_time_cpu': 60,
                    'limit_time_real': 61,
                    'limit_time_real_cron': 62,
                    'limit_request': 100,
                }
            )
        self.assertEqual(config.options, values)
