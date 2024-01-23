import unittest

import odoo
from odoo.tests import TransactionCase
from odoo.tools import file_path, file_open, file_open_temporary_directory
from odoo.tools.config import configmanager, _get_default_datadir


IS_POSIX = 'workers' in odoo.tools.config.options
ROOT_PATH = odoo.tools.config.options['root_path'].removesuffix('/odoo')


class TestConfigManager(TransactionCase):
    maxDiff = None

    def test_01_default_config(self):
        config = configmanager(fname=file_path('base/tests/config/empty.conf'))

        default_values = {
            # options not exposed on the command line
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'publisher_warranty_url': 'http://services.openerp.com/publisher-warranty/',
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
            'longpolling_port': 0,
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
                    'limit_memory_hard': 2560 * 1024 * 1024,
                    'limit_time_cpu': 60,
                    'limit_time_real': 120,
                    'limit_time_real_cron': -1,
                    'limit_request': 2**16,
                }
            )

        config._parse_config()
        self.assertEqual(config.options, default_values, "Options don't match")

    def test_02_default_config_file(self):
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
            'config': '/foo/bar/config',  # blacklist for save, read from the config file
            'save': True,  # blacklist for save, read from the config file
            'init': {},  # blacklist for save, ignored from the config file
            'update': {},  # blacklist for save, ignored from the config file
            'without_demo': True,
            'demo': {},  # blacklist for save, ignored from the config file
            'import_partial': 'bob',
            'pidfile': '/binary/pg_pid',
            'addons_path': '/foo/bar/odoo',
            'upgrade_path': '/foo/bar/upgrade',
            'server_wide_modules': 'base,web,mail',
            'data_dir': '/home/navy/.local/share/Odoo',

            # HTTP
            'http_interface': '10.0.0.254',
            'http_port': 6942,
            'gevent_port': 8012,
            'longpolling_port': 0,
            'http_enable': False,
            'proxy_mode': True,
            'x_sendfile': True,

            # web
            'dbfilter': '.*',

            # testing
            'test_file': '/dev/null',
            'test_enable': True,
            'test_tags': ':TestMantra.test_is_extra_mile_done',
            'screencasts': '/temp/screencasts',
            'screenshots': '/temp/screenshots',

            # logging
            'logfile': '/foo/bar/odoo.log',
            'syslog': True,
            'log_handler': [':DEBUG'],
            'log_db': True,
            'log_db_level': 'debug',
            'log_level': 'debug',

            # SMTP
            'email_from': 'admin@example.com',
            'from_filter': '.*',
            'smtp_server': 'localhoost',
            'smtp_port': 12,
            'smtp_ssl': True,
            'smtp_user': 'spongebob',
            'smtp_password': 'Tigrou007',
            'smtp_ssl_certificate_filename': '/var/www/cert',
            'smtp_ssl_private_key_filename': '/var/www/key',

            # database
            'db_name': 'horizon',
            'db_user': 'kiwi',
            'db_password': 'Tigrou007',
            'pg_path': '/binary/pg_path',
            'db_host': True,
            'db_port': 4269,
            'db_sslmode': 'verify-full',
            'db_maxconn': 42,
            'db_maxconn_gevent': True,
            'db_template': 'backup1706',
            'db_replica_host': '192.168.0.255',
            'db_replica_port': 2038,

            # i18n
            'load_language': 'fr_FR',  # blacklist for save, read from the config file
            'language': 'fr_FR',  # blacklist for save, read from the config file
            'translate_out': '/foo/bar/translate_out.csv',  # blacklist for save, read from the config file
            'translate_in': '/foo/bar/translate_in.csv',  # blacklist for save, read from the config file
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
            'unaccent': True,
            'geoip_city_db': '/foo/bar/city.db',
            'geoip_country_db': '/foo/bar/country.db',
        }

        if IS_POSIX:
            # multiprocessing
            values.update(
                {
                    'workers': 92,
                    'limit_memory_soft': 1234,
                    'limit_memory_hard': 5678,
                    'limit_time_cpu': 3,
                    'limit_time_real': 4,
                    'limit_time_real_cron': -3,
                    'limit_request': 1,
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
