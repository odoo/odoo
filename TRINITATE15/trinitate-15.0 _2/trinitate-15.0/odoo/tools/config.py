# Part of Odoo. See LICENSE file for full copyright and licensing details.

import configparser as ConfigParser
import errno
import logging
import optparse
import glob
import os
import sys
import tempfile
import warnings
import odoo
from os.path import expandvars, expanduser, abspath, realpath, normcase
from .. import release, conf, loglevels
from . import appdirs

from passlib.context import CryptContext
crypt_context = CryptContext(schemes=['pbkdf2_sha512', 'plaintext'],
                             deprecated=['plaintext'])

class MyOption (optparse.Option, object):
    """ optparse Option with two additional attributes.

    The list of command line options (getopt.Option) is used to create the
    list of the configuration file options. When reading the file, and then
    reading the command line arguments, we don't want optparse.parse results
    to override the configuration file values. But if we provide default
    values to optparse, optparse will return them and we can't know if they
    were really provided by the user or not. A solution is to not use
    optparse's default attribute, but use a custom one (that will be copied
    to create the default values of the configuration file).

    """
    def __init__(self, *opts, **attrs):
        self.my_default = attrs.pop('my_default', None)
        super(MyOption, self).__init__(*opts, **attrs)

DEFAULT_LOG_HANDLER = ':INFO'
def _get_default_datadir():
    home = os.path.expanduser('~')
    if os.path.isdir(home):
        func = appdirs.user_data_dir
    else:
        if sys.platform in ['win32', 'darwin']:
            func = appdirs.site_data_dir
        else:
            func = lambda **kwarg: "/var/lib/%s" % kwarg['appname'].lower()
    # No "version" kwarg as session and filestore paths are shared against series
    return func(appname=release.product_name, appauthor=release.author)

def _deduplicate_loggers(loggers):
    """ Avoid saving multiple logging levels for the same loggers to a save
    file, that just takes space and the list can potentially grow unbounded
    if for some odd reason people use :option`--save`` all the time.
    """
    # dict(iterable) -> the last item of iterable for any given key wins,
    # which is what we want and expect. Output order should not matter as
    # there are no duplicates within the output sequence
    return (
        '{}:{}'.format(logger, level)
        for logger, level in dict(it.split(':') for it in loggers).items()
    )

class configmanager(object):
    def __init__(self, fname=None):
        """Constructor.

        :param fname: a shortcut allowing to instantiate :class:`configmanager`
                      from Python code without resorting to environment
                      variable
        """
        # Options not exposed on the command line. Command line options will be added
        # from optparse's parser.
        self.options = {
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'publisher_warranty_url': 'http://services.openerp.com/publisher-warranty/',
            'reportgz': False,
            'root_path': None,
            'websocket_keep_alive_timeout': 3600,
            'websocket_rate_limit_burst': 10,
            'websocket_rate_limit_delay': 0.2,
        }

        # Not exposed in the configuration file.
        self.blacklist_for_save = set([
            'publisher_warranty_url', 'load_language', 'root_path',
            'init', 'save', 'config', 'update', 'stop_after_init', 'dev_mode', 'shell_interface',
            'longpolling_port',
        ])

        # dictionary mapping option destination (keys in self.options) to MyOptions.
        self.casts = {}

        self.misc = {}
        self.config_file = fname

        self._LOGLEVELS = dict([
            (getattr(loglevels, 'LOG_%s' % x), getattr(logging, x))
            for x in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET')
        ])

        version = "%s %s" % (release.description, release.version)
        self.parser = parser = optparse.OptionParser(version=version, option_class=MyOption)

        # Server startup config
        group = optparse.OptionGroup(parser, "Common options")
        group.add_option("-c", "--config", dest="config", help="specify alternate config file")
        group.add_option("-s", "--save", action="store_true", dest="save", default=False,
                          help="save configuration to ~/.odoorc (or to ~/.openerp_serverrc if it exists)")
        group.add_option("-i", "--init", dest="init", help="install one or more modules (comma-separated list, use \"all\" for all modules), requires -d")
        group.add_option("-u", "--update", dest="update",
                          help="update one or more modules (comma-separated list, use \"all\" for all modules). Requires -d.")
        group.add_option("--without-demo", dest="without_demo",
                          help="disable loading demo data for modules to be installed (comma-separated, use \"all\" for all modules). Requires -d and -i. Default is %default",
                          my_default=False)
        group.add_option("-P", "--import-partial", dest="import_partial", my_default='',
                        help="Use this for big data importation, if it crashes you will be able to continue at the current state. Provide a filename to store intermediate importation states.")
        group.add_option("--pidfile", dest="pidfile", help="file where the server pid will be stored")
        group.add_option("--addons-path", dest="addons_path",
                         help="specify additional addons paths (separated by commas).",
                         action="callback", callback=self._check_addons_path, nargs=1, type="string")
        group.add_option("--upgrade-path", dest="upgrade_path",
                         help="specify an additional upgrade path.",
                         action="callback", callback=self._check_upgrade_path, nargs=1, type="string")
        group.add_option("--load", dest="server_wide_modules", help="Comma-separated list of server-wide modules.", my_default='base,web')

        group.add_option("-D", "--data-dir", dest="data_dir", my_default=_get_default_datadir(),
                         help="Directory where to store Odoo data")
        parser.add_option_group(group)

        # HTTP
        group = optparse.OptionGroup(parser, "HTTP Service Configuration")
        group.add_option("--http-interface", dest="http_interface", my_default='',
                         help="Listen interface address for HTTP services. "
                              "Keep empty to listen on all interfaces (0.0.0.0)")
        group.add_option("-p", "--http-port", dest="http_port", my_default=8069,
                         help="Listen port for the main HTTP service", type="int", metavar="PORT")
        group.add_option("--longpolling-port", dest="longpolling_port", my_default=0,
                         help="Deprecated alias to the gevent-port option", type="int", metavar="PORT")
        group.add_option("--gevent-port", dest="gevent_port", my_default=8072,
                         help="Listen port for the gevent worker", type="int", metavar="PORT")
        group.add_option("--no-http", dest="http_enable", action="store_false", my_default=True,
                         help="Disable the HTTP and Longpolling services entirely")
        group.add_option("--proxy-mode", dest="proxy_mode", action="store_true", my_default=False,
                         help="Activate reverse proxy WSGI wrappers (headers rewriting) "
                              "Only enable this when running behind a trusted web proxy!")
        group.add_option("--x-sendfile", dest="x_sendfile", action="store_true", my_default=False,
                         help="Activate X-Sendfile (apache) and X-Accel-Redirect (nginx) "
                              "HTTP response header to delegate the delivery of large "
                              "files (assets/attachments) to the web server.")
        # HTTP: hidden backwards-compatibility for "*xmlrpc*" options
        hidden = optparse.SUPPRESS_HELP
        group.add_option("--xmlrpc-interface", dest="http_interface", help=hidden)
        group.add_option("--xmlrpc-port", dest="http_port", type="int", help=hidden)
        group.add_option("--no-xmlrpc", dest="http_enable", action="store_false", help=hidden)

        parser.add_option_group(group)

        # WEB
        group = optparse.OptionGroup(parser, "Web interface Configuration")
        group.add_option("--db-filter", dest="dbfilter", my_default='', metavar="REGEXP",
                         help="Regular expressions for filtering available databases for Web UI. "
                              "The expression can use %d (domain) and %h (host) placeholders.")
        parser.add_option_group(group)

        # Testing Group
        group = optparse.OptionGroup(parser, "Testing Configuration")
        group.add_option("--test-file", dest="test_file", my_default=False,
                         help="Launch a python test file.")
        group.add_option("--test-enable", action="callback", callback=self._test_enable_callback,
                         dest='test_enable',
                         help="Enable unit tests.")
        group.add_option("--test-tags", dest="test_tags",
                         help="Comma-separated list of specs to filter which tests to execute. Enable unit tests if set. "
                         "A filter spec has the format: [-][tag][/module][:class][.method] "
                         "The '-' specifies if we want to include or exclude tests matching this spec. "
                         "The tag will match tags added on a class with a @tagged decorator "
                         "(all Test classes have 'standard' and 'at_install' tags "
                         "until explicitly removed, see the decorator documentation). "
                         "'*' will match all tags. "
                         "If tag is omitted on include mode, its value is 'standard'. "
                         "If tag is omitted on exclude mode, its value is '*'. "
                         "The module, class, and method will respectively match the module name, test class name and test method name. "
                         "Example: --test-tags :TestClass.test_func,/test_module,external "

                         "Filtering and executing the tests happens twice: right "
                         "after each module installation/update and at the end "
                         "of the modules loading. At each stage tests are filtered "
                         "by --test-tags specs and additionally by dynamic specs "
                         "'at_install' and 'post_install' correspondingly.")

        group.add_option("--screencasts", dest="screencasts", action="store", my_default=None,
                         metavar='DIR',
                         help="Screencasts will go in DIR/{db_name}/screencasts.")
        temp_tests_dir = os.path.join(tempfile.gettempdir(), 'odoo_tests')
        group.add_option("--screenshots", dest="screenshots", action="store", my_default=temp_tests_dir,
                         metavar='DIR',
                         help="Screenshots will go in DIR/{db_name}/screenshots. Defaults to %s." % temp_tests_dir)
        parser.add_option_group(group)

        # Logging Group
        group = optparse.OptionGroup(parser, "Logging Configuration")
        group.add_option("--logfile", dest="logfile", help="file where the server log will be stored")
        group.add_option("--syslog", action="store_true", dest="syslog", my_default=False, help="Send the log to the syslog server")
        group.add_option('--log-handler', action="append", default=[], my_default=DEFAULT_LOG_HANDLER, metavar="PREFIX:LEVEL", help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')
        group.add_option('--log-web', action="append_const", dest="log_handler", const="odoo.http:DEBUG", help='shortcut for --log-handler=odoo.http:DEBUG')
        group.add_option('--log-sql', action="append_const", dest="log_handler", const="odoo.sql_db:DEBUG", help='shortcut for --log-handler=odoo.sql_db:DEBUG')
        group.add_option('--log-db', dest='log_db', help="Logging database", my_default=False)
        group.add_option('--log-db-level', dest='log_db_level', my_default='warning', help="Logging database level")
        # For backward-compatibility, map the old log levels to something
        # quite close.
        levels = [
            'info', 'debug_rpc', 'warn', 'test', 'critical', 'runbot',
            'debug_sql', 'error', 'debug', 'debug_rpc_answer', 'notset'
        ]
        group.add_option('--log-level', dest='log_level', type='choice',
                         choices=levels, my_default='info',
                         help='specify the level of the logging. Accepted values: %s.' % (levels,))

        parser.add_option_group(group)

        # SMTP Group
        group = optparse.OptionGroup(parser, "SMTP Configuration")
        group.add_option('--email-from', dest='email_from', my_default=False,
                         help='specify the SMTP email address for sending email')
        group.add_option('--from-filter', dest='from_filter', my_default=False,
                         help='specify for which email address the SMTP configuration can be used')
        group.add_option('--smtp', dest='smtp_server', my_default='localhost',
                         help='specify the SMTP server for sending email')
        group.add_option('--smtp-port', dest='smtp_port', my_default=25,
                         help='specify the SMTP port', type="int")
        group.add_option('--smtp-ssl', dest='smtp_ssl', action='store_true', my_default=False,
                         help='if passed, SMTP connections will be encrypted with SSL (STARTTLS)')
        group.add_option('--smtp-user', dest='smtp_user', my_default=False,
                         help='specify the SMTP username for sending email')
        group.add_option('--smtp-password', dest='smtp_password', my_default=False,
                         help='specify the SMTP password for sending email')
        group.add_option('--smtp-ssl-certificate-filename', dest='smtp_ssl_certificate_filename', my_default=False,
                         help='specify the SSL certificate used for authentication')
        group.add_option('--smtp-ssl-private-key-filename', dest='smtp_ssl_private_key_filename', my_default=False,
                         help='specify the SSL private key used for authentication')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Database related options")
        group.add_option("-d", "--database", dest="db_name", my_default=False,
                         help="specify the database name")
        group.add_option("-r", "--db_user", dest="db_user", my_default=False,
                         help="specify the database user name")
        group.add_option("-w", "--db_password", dest="db_password", my_default=False,
                         help="specify the database password")
        group.add_option("--pg_path", dest="pg_path", help="specify the pg executable path")
        group.add_option("--db_host", dest="db_host", my_default=False,
                         help="specify the database host")
        group.add_option("--db_port", dest="db_port", my_default=False,
                         help="specify the database port", type="int")
        group.add_option("--db_sslmode", dest="db_sslmode", type="choice", my_default='prefer',
                         choices=['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'],
                         help="specify the database ssl connection mode (see PostgreSQL documentation)")
        group.add_option("--db_maxconn", dest="db_maxconn", type='int', my_default=64,
                         help="specify the maximum number of physical connections to PostgreSQL")
        group.add_option("--db-template", dest="db_template", my_default="template0",
                         help="specify a custom database template to create a new database")
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Internationalisation options",
            "Use these options to translate Odoo to another language. "
            "See i18n section of the user manual. Option '-d' is mandatory. "
            "Option '-l' is mandatory in case of importation"
            )
        group.add_option('--load-language', dest="load_language",
                         help="specifies the languages for the translations you want to be loaded")
        group.add_option('-l', "--language", dest="language",
                         help="specify the language of the translation file. Use it with --i18n-export or --i18n-import")
        group.add_option("--i18n-export", dest="translate_out",
                         help="export all sentences to be translated to a CSV file, a PO file or a TGZ archive and exit")
        group.add_option("--i18n-import", dest="translate_in",
                         help="import a CSV or a PO file with translations and exit. The '-l' option is required.")
        group.add_option("--i18n-overwrite", dest="overwrite_existing_translations", action="store_true", my_default=False,
                         help="overwrites existing translation terms on updating a module or importing a CSV or a PO file.")
        group.add_option("--modules", dest="translate_modules",
                         help="specify modules to export. Use in combination with --i18n-export")
        parser.add_option_group(group)

        security = optparse.OptionGroup(parser, 'Security-related options')
        security.add_option('--no-database-list', action="store_false", dest='list_db', my_default=True,
                            help="Disable the ability to obtain or view the list of databases. "
                                 "Also disable access to the database manager and selector, "
                                 "so be sure to set a proper --database parameter first")
        parser.add_option_group(security)

        # Advanced options
        group = optparse.OptionGroup(parser, "Advanced options")
        group.add_option('--dev', dest='dev_mode', type="string",
                         help="Enable developer mode. Param: List of options separated by comma. "
                              "Options : all, reload, qweb, xml")
        group.add_option('--shell-interface', dest='shell_interface', type="string",
                         help="Specify a preferred REPL to use in shell mode. Supported REPLs are: "
                              "[ipython|ptpython|bpython|python]")
        group.add_option("--stop-after-init", action="store_true", dest="stop_after_init", my_default=False,
                          help="stop the server after its initialization")
        group.add_option("--osv-memory-count-limit", dest="osv_memory_count_limit", my_default=0,
                         help="Force a limit on the maximum number of records kept in the virtual "
                              "osv_memory tables. By default there is no limit.",
                         type="int")
        group.add_option("--transient-age-limit", dest="transient_age_limit", my_default=1.0,
                         help="Time limit (decimal value in hours) records created with a "
                              "TransientModel (mostly wizard) are kept in the database. Default to 1 hour.",
                         type="float")
        group.add_option("--osv-memory-age-limit", dest="osv_memory_age_limit", my_default=False,
                         help="Deprecated alias to the transient-age-limit option",
                         type="float")
        group.add_option("--max-cron-threads", dest="max_cron_threads", my_default=2,
                         help="Maximum number of threads processing concurrently cron jobs (default 2).",
                         type="int")
        group.add_option("--unaccent", dest="unaccent", my_default=False, action="store_true",
                         help="Try to enable the unaccent extension when creating new databases.")
        group.add_option("--geoip-db", dest="geoip_database", my_default='/usr/share/GeoIP/GeoLite2-City.mmdb',
                         help="Absolute path to the GeoIP database file.")
        parser.add_option_group(group)

        if os.name == 'posix':
            group = optparse.OptionGroup(parser, "Multiprocessing options")
            # TODO sensible default for the three following limits.
            group.add_option("--workers", dest="workers", my_default=0,
                             help="Specify the number of workers, 0 disable prefork mode.",
                             type="int")
            group.add_option("--limit-memory-soft", dest="limit_memory_soft", my_default=2048 * 1024 * 1024,
                             help="Maximum allowed virtual memory per worker (in bytes), when reached the worker be "
                             "reset after the current request (default 2048MiB).",
                             type="int")
            group.add_option("--limit-memory-hard", dest="limit_memory_hard", my_default=2560 * 1024 * 1024,
                             help="Maximum allowed virtual memory per worker (in bytes), when reached, any memory "
                             "allocation will fail (default 2560MiB).",
                             type="int")
            group.add_option("--limit-time-cpu", dest="limit_time_cpu", my_default=60,
                             help="Maximum allowed CPU time per request (default 60).",
                             type="int")
            group.add_option("--limit-time-real", dest="limit_time_real", my_default=120,
                             help="Maximum allowed Real time per request (default 120).",
                             type="int")
            group.add_option("--limit-time-real-cron", dest="limit_time_real_cron", my_default=-1,
                             help="Maximum allowed Real time per cron job. (default: --limit-time-real). "
                                  "Set to 0 for no limit. ",
                             type="int")
            group.add_option("--limit-request", dest="limit_request", my_default=2**16,
                             help="Maximum number of request to be processed per worker (default 65536).",
                             type="int")
            parser.add_option_group(group)

        # Copy all optparse options (i.e. MyOption) into self.options.
        for group in parser.option_groups:
            for option in group.option_list:
                if option.dest not in self.options:
                    self.options[option.dest] = option.my_default
                    self.casts[option.dest] = option

        # generate default config
        self._parse_config()

    def parse_config(self, args=None):
        """ Parse the configuration file (if any) and the command-line
        arguments.

        This method initializes odoo.tools.config and openerp.conf (the
        former should be removed in the future) with library-wide
        configuration values.

        This method must be called before proper usage of this library can be
        made.

        Typical usage of this method:

            odoo.tools.config.parse_config(sys.argv[1:])
        """
        opt = self._parse_config(args)
        odoo.netsvc.init_logger()
        self._warn_deprecated_options()
        odoo.modules.module.initialize_sys_path()
        return opt

    def _parse_config(self, args=None):
        if args is None:
            args = []
        opt, args = self.parser.parse_args(args)

        def die(cond, msg):
            if cond:
                self.parser.error(msg)

        # Ensures no illegitimate argument is silently discarded (avoids insidious "hyphen to dash" problem)
        die(args, "unrecognized parameters: '%s'" % " ".join(args))

        die(bool(opt.syslog) and bool(opt.logfile),
            "the syslog and logfile options are exclusive")

        die(opt.translate_in and (not opt.language or not opt.db_name),
            "the i18n-import option cannot be used without the language (-l) and the database (-d) options")

        die(opt.overwrite_existing_translations and not (opt.translate_in or opt.update),
            "the i18n-overwrite option cannot be used without the i18n-import option or without the update option")

        die(opt.translate_out and (not opt.db_name),
            "the i18n-export option cannot be used without the database (-d) option")

        # Check if the config file exists (-c used, but not -s)
        die(not opt.save and opt.config and not os.access(opt.config, os.R_OK),
            "The config file '%s' selected with -c/--config doesn't exist or is not readable, "\
            "use -s/--save if you want to generate it"% opt.config)

        die(bool(opt.osv_memory_age_limit) and bool(opt.transient_memory_age_limit),
            "the osv-memory-count-limit option cannot be used with the "
            "transient-age-limit option, please only use the latter.")

        # place/search the config file on Win32 near the server installation
        # (../etc from the server)
        # if the server is run by an unprivileged user, he has to specify location of a config file where he has the rights to write,
        # else he won't be able to save the configurations, or even to start the server...
        # TODO use appdirs
        if os.name == 'nt':
            rcfilepath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'odoo.conf')
        else:
            rcfilepath = os.path.expanduser('~/.odoorc')
            old_rcfilepath = os.path.expanduser('~/.openerp_serverrc')

            die(os.path.isfile(rcfilepath) and os.path.isfile(old_rcfilepath),
                "Found '.odoorc' and '.openerp_serverrc' in your path. Please keep only one of "\
                "them, preferably '.odoorc'.")

            if not os.path.isfile(rcfilepath) and os.path.isfile(old_rcfilepath):
                rcfilepath = old_rcfilepath

        self.rcfile = os.path.abspath(
            self.config_file or opt.config or os.environ.get('ODOO_RC') or os.environ.get('OPENERP_SERVER') or rcfilepath)
        self.load()

        # Verify that we want to log or not, if not the output will go to stdout
        if self.options['logfile'] in ('None', 'False'):
            self.options['logfile'] = False
        # the same for the pidfile
        if self.options['pidfile'] in ('None', 'False'):
            self.options['pidfile'] = False
        # the same for the test_tags
        if self.options['test_tags'] == 'None':
            self.options['test_tags'] = None
        # and the server_wide_modules
        if self.options['server_wide_modules'] in ('', 'None', 'False'):
            self.options['server_wide_modules'] = 'base,web'

        # if defined do not take the configfile value even if the defined value is None
        keys = ['gevent_port', 'http_interface', 'http_port', 'longpolling_port', 'http_enable', 'x_sendfile',
                'db_name', 'db_user', 'db_password', 'db_host', 'db_sslmode',
                'db_port', 'db_template', 'logfile', 'pidfile', 'smtp_port',
                'email_from', 'smtp_server', 'smtp_user', 'smtp_password', 'from_filter',
                'smtp_ssl_certificate_filename', 'smtp_ssl_private_key_filename',
                'db_maxconn', 'import_partial', 'addons_path', 'upgrade_path',
                'syslog', 'without_demo', 'screencasts', 'screenshots',
                'dbfilter', 'log_level', 'log_db',
                'log_db_level', 'geoip_database', 'dev_mode', 'shell_interface'
        ]

        for arg in keys:
            # Copy the command-line argument (except the special case for log_handler, due to
            # action=append requiring a real default, so we cannot use the my_default workaround)
            if getattr(opt, arg, None) is not None:
                self.options[arg] = getattr(opt, arg)
            # ... or keep, but cast, the config file value.
            elif isinstance(self.options[arg], str) and self.casts[arg].type in optparse.Option.TYPE_CHECKER:
                self.options[arg] = optparse.Option.TYPE_CHECKER[self.casts[arg].type](self.casts[arg], arg, self.options[arg])

        if isinstance(self.options['log_handler'], str):
            self.options['log_handler'] = self.options['log_handler'].split(',')
        self.options['log_handler'].extend(opt.log_handler)

        # if defined but None take the configfile value
        keys = [
            'language', 'translate_out', 'translate_in', 'overwrite_existing_translations',
            'dev_mode', 'shell_interface', 'smtp_ssl', 'load_language',
            'stop_after_init', 'without_demo', 'http_enable', 'syslog',
            'list_db', 'proxy_mode',
            'test_file', 'test_tags',
            'osv_memory_count_limit', 'osv_memory_age_limit', 'transient_age_limit', 'max_cron_threads', 'unaccent',
            'data_dir',
            'server_wide_modules',
        ]

        posix_keys = [
            'workers',
            'limit_memory_hard', 'limit_memory_soft',
            'limit_time_cpu', 'limit_time_real', 'limit_request', 'limit_time_real_cron'
        ]

        if os.name == 'posix':
            keys += posix_keys
        else:
            self.options.update(dict.fromkeys(posix_keys, None))

        # Copy the command-line arguments...
        for arg in keys:
            if getattr(opt, arg) is not None:
                self.options[arg] = getattr(opt, arg)
            # ... or keep, but cast, the config file value.
            elif isinstance(self.options[arg], str) and self.casts[arg].type in optparse.Option.TYPE_CHECKER:
                self.options[arg] = optparse.Option.TYPE_CHECKER[self.casts[arg].type](self.casts[arg], arg, self.options[arg])

        self.options['root_path'] = self._normalize(os.path.join(os.path.dirname(__file__), '..'))
        if not self.options['addons_path'] or self.options['addons_path']=='None':
            default_addons = []
            base_addons = os.path.join(self.options['root_path'], 'addons')
            if os.path.exists(base_addons):
                default_addons.append(base_addons)
            main_addons = os.path.abspath(os.path.join(self.options['root_path'], '../addons'))
            if os.path.exists(main_addons):
                default_addons.append(main_addons)
            self.options['addons_path'] = ','.join(default_addons)
        else:
            self.options['addons_path'] = ",".join(
                self._normalize(x)
                for x in self.options['addons_path'].split(','))

        self.options["upgrade_path"] = (
            ",".join(self._normalize(x)
                for x in self.options['upgrade_path'].split(','))
            if self.options['upgrade_path']
            else ""
        )

        self.options['init'] = opt.init and dict.fromkeys(opt.init.split(','), 1) or {}
        self.options['demo'] = (dict(self.options['init'])
                                if not self.options['without_demo'] else {})
        self.options['update'] = opt.update and dict.fromkeys(opt.update.split(','), 1) or {}
        self.options['translate_modules'] = opt.translate_modules and [m.strip() for m in opt.translate_modules.split(',')] or ['all']
        self.options['translate_modules'].sort()

        dev_split = [s.strip() for s in opt.dev_mode.split(',')] if opt.dev_mode else []
        self.options['dev_mode'] = dev_split + (['reload', 'qweb', 'xml'] if 'all' in dev_split else [])

        if opt.pg_path:
            self.options['pg_path'] = opt.pg_path

        self.options['test_enable'] = bool(self.options['test_tags'])

        if opt.save:
            self.save()

        # normalize path options
        for key in ['data_dir', 'logfile', 'pidfile', 'test_file', 'screencasts', 'screenshots', 'pg_path', 'translate_out', 'translate_in', 'geoip_database']:
            self.options[key] = self._normalize(self.options[key])

        conf.addons_paths = self.options['addons_path'].split(',')

        conf.server_wide_modules = [
            m.strip() for m in self.options['server_wide_modules'].split(',') if m.strip()
        ]
        return opt

    def _warn_deprecated_options(self):
        if self.options['osv_memory_age_limit']:
            warnings.warn(
                "The osv-memory-age-limit is a deprecated alias to "
                "the transient-age-limit option, please use the latter.",
                DeprecationWarning)
            self.options['transient_age_limit'] = self.options.pop('osv_memory_age_limit')
        if self.options['longpolling_port']:
            warnings.warn(
                "The longpolling-port is a deprecated alias to "
                "the gevent-port option, please use the latter.",
                DeprecationWarning)
            self.options['gevent_port'] = self.options.pop('longpolling_port')

    def _is_addons_path(self, path):
        from odoo.modules.module import MANIFEST_NAMES
        for f in os.listdir(path):
            modpath = os.path.join(path, f)
            if os.path.isdir(modpath):
                def hasfile(filename):
                    return os.path.isfile(os.path.join(modpath, filename))
                if hasfile('__init__.py') and any(hasfile(mname) for mname in MANIFEST_NAMES):
                    return True
        return False

    def _check_addons_path(self, option, opt, value, parser):
        ad_paths = []
        for path in value.split(','):
            path = path.strip()
            res = os.path.abspath(os.path.expanduser(path))
            if not os.path.isdir(res):
                raise optparse.OptionValueError("option %s: no such directory: %r" % (opt, res))
            if not self._is_addons_path(res):
                raise optparse.OptionValueError("option %s: the path %r is not a valid addons directory" % (opt, path))
            ad_paths.append(res)

        setattr(parser.values, option.dest, ",".join(ad_paths))

    def _check_upgrade_path(self, option, opt, value, parser):
        upgrade_path = []
        for path in value.split(','):
            path = path.strip()
            res = self._normalize(path)
            if not os.path.isdir(res):
                raise optparse.OptionValueError("option %s: no such directory: %r" % (opt, path))
            if not self._is_upgrades_path(res):
                raise optparse.OptionValueError("option %s: the path %r is not a valid upgrade directory" % (opt, path))
            if res not in upgrade_path:
                upgrade_path.append(res)
        setattr(parser.values, option.dest, ",".join(upgrade_path))

    def _is_upgrades_path(self, res):
        return any(
            glob.glob(os.path.join(res, f"*/*/{prefix}-*.py"))
            for prefix in ["pre", "post", "end"]
        )

    def _test_enable_callback(self, option, opt, value, parser):
        if not parser.values.test_tags:
            parser.values.test_tags = "+standard"

    def load(self):
        outdated_options_map = {
            'xmlrpc_port': 'http_port',
            'xmlrpc_interface': 'http_interface',
            'xmlrpc': 'http_enable',
        }
        p = ConfigParser.RawConfigParser()
        try:
            p.read([self.rcfile])
            for (name,value) in p.items('options'):
                name = outdated_options_map.get(name, name)
                if value=='True' or value=='true':
                    value = True
                if value=='False' or value=='false':
                    value = False
                self.options[name] = value
            #parse the other sections, as well
            for sec in p.sections():
                if sec == 'options':
                    continue
                self.misc.setdefault(sec, {})
                for (name, value) in p.items(sec):
                    if value=='True' or value=='true':
                        value = True
                    if value=='False' or value=='false':
                        value = False
                    self.misc[sec][name] = value
        except IOError:
            pass
        except ConfigParser.NoSectionError:
            pass

    def save(self, keys=None):
        p = ConfigParser.RawConfigParser()
        loglevelnames = dict(zip(self._LOGLEVELS.values(), self._LOGLEVELS))
        rc_exists = os.path.exists(self.rcfile)
        if rc_exists and keys:
            p.read([self.rcfile])
        if not p.has_section('options'):
            p.add_section('options')
        for opt in sorted(self.options):
            if keys is not None and opt not in keys:
                continue
            if opt in ('version', 'language', 'translate_out', 'translate_in', 'overwrite_existing_translations', 'init', 'update'):
                continue
            if opt in self.blacklist_for_save:
                continue
            if opt in ('log_level',):
                p.set('options', opt, loglevelnames.get(self.options[opt], self.options[opt]))
            elif opt == 'log_handler':
                p.set('options', opt, ','.join(_deduplicate_loggers(self.options[opt])))
            else:
                p.set('options', opt, self.options[opt])

        for sec in sorted(self.misc):
            p.add_section(sec)
            for opt in sorted(self.misc[sec]):
                p.set(sec,opt,self.misc[sec][opt])

        # try to create the directories and write the file
        try:
            if not rc_exists and not os.path.exists(os.path.dirname(self.rcfile)):
                os.makedirs(os.path.dirname(self.rcfile))
            try:
                p.write(open(self.rcfile, 'w'))
                if not rc_exists:
                    os.chmod(self.rcfile, 0o600)
            except IOError:
                sys.stderr.write("ERROR: couldn't write the config file\n")

        except OSError:
            # what to do if impossible?
            sys.stderr.write("ERROR: couldn't create the config directory\n")

    def get(self, key, default=None):
        return self.options.get(key, default)

    def pop(self, key, default=None):
        return self.options.pop(key, default)

    def get_misc(self, sect, key, default=None):
        return self.misc.get(sect,{}).get(key, default)

    def __setitem__(self, key, value):
        self.options[key] = value
        if key in self.options and isinstance(self.options[key], str) and \
                key in self.casts and self.casts[key].type in optparse.Option.TYPE_CHECKER:
            self.options[key] = optparse.Option.TYPE_CHECKER[self.casts[key].type](self.casts[key], key, self.options[key])

    def __getitem__(self, key):
        return self.options[key]

    @property
    def addons_data_dir(self):
        add_dir = os.path.join(self['data_dir'], 'addons')
        d = os.path.join(add_dir, release.series)
        if not os.path.exists(d):
            try:
                # bootstrap parent dir +rwx
                if not os.path.exists(add_dir):
                    os.makedirs(add_dir, 0o700)
                # try to make +rx placeholder dir, will need manual +w to activate it
                os.makedirs(d, 0o500)
            except OSError:
                logging.getLogger(__name__).debug('Failed to create addons data dir %s', d)
        return d

    @property
    def session_dir(self):
        d = os.path.join(self['data_dir'], 'sessions')
        try:
            os.makedirs(d, 0o700)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
            assert os.access(d, os.W_OK), \
                "%s: directory is not writable" % d
        return d

    def filestore(self, dbname):
        return os.path.join(self['data_dir'], 'filestore', dbname)

    def set_admin_password(self, new_password):
        hash_password = crypt_context.hash if hasattr(crypt_context, 'hash') else crypt_context.encrypt
        self.options['admin_passwd'] = hash_password(new_password)

    def verify_admin_password(self, password):
        """Verifies the super-admin password, possibly updating the stored hash if needed"""
        stored_hash = self.options['admin_passwd']
        if not stored_hash:
            # empty password/hash => authentication forbidden
            return False
        result, updated_hash = crypt_context.verify_and_update(password, stored_hash)
        if result:
            if updated_hash:
                self.options['admin_passwd'] = updated_hash
            return True

    def _normalize(self, path):
        if not path:
            return ''
        return normcase(realpath(abspath(expanduser(expandvars(path.strip())))))


config = configmanager()
