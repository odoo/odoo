#odoo.loggers.handlers. -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    import configparser as ConfigParser
except ImportError:
    import ConfigParser
import optparse
import os
import sys
import odoo
import odoo.conf
import odoo.loglevels as loglevels
import logging
import odoo.release as release
from . import appdirs, pycompat


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
        for logger, level in pycompat.items(dict(it.split(':') for it in loggers))
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
        }

        # Not exposed in the configuration file.
        self.blacklist_for_save = set([
            'publisher_warranty_url', 'load_language', 'root_path',
            'init', 'save', 'config', 'update', 'stop_after_init', 'dev_mode', 'shell_interface'
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
        group.add_option("--load", dest="server_wide_modules", help="Comma-separated list of server-wide modules.", my_default='web')

        group.add_option("-D", "--data-dir", dest="data_dir", my_default=_get_default_datadir(),
                         help="Directory where to store Odoo data")
        parser.add_option_group(group)

        # XML-RPC / HTTP
        group = optparse.OptionGroup(parser, "XML-RPC Configuration")
        group.add_option("--xmlrpc-interface", dest="xmlrpc_interface", my_default='',
                         help="Specify the TCP IP address for the XML-RPC protocol. The empty string binds to all interfaces.")
        group.add_option("--xmlrpc-port", dest="xmlrpc_port", my_default=8069,
                         help="specify the TCP port for the XML-RPC protocol", type="int")
        group.add_option("--no-xmlrpc", dest="xmlrpc", action="store_false", my_default=True,
                         help="disable the XML-RPC protocol")
        group.add_option("--proxy-mode", dest="proxy_mode", action="store_true", my_default=False,
                         help="Enable correct behavior when behind a reverse proxy")
        group.add_option("--longpolling-port", dest="longpolling_port", my_default=8072,
                         help="specify the TCP port for longpolling requests", type="int")
        parser.add_option_group(group)

        # WEB
        group = optparse.OptionGroup(parser, "Web interface Configuration")
        group.add_option("--db-filter", dest="dbfilter", my_default='.*',
                         help="Filter listed database", metavar="REGEXP")
        parser.add_option_group(group)

        # Testing Group
        group = optparse.OptionGroup(parser, "Testing Configuration")
        group.add_option("--test-file", dest="test_file", my_default=False,
                         help="Launch a python or YML test file.")
        group.add_option("--test-report-directory", dest="test_report_directory", my_default=False,
                         help="If set, will save sample of all reports in this directory.")
        group.add_option("--test-enable", action="store_true", dest="test_enable",
                         my_default=False, help="Enable YAML and unit tests.")
        group.add_option("--test-commit", action="store_true", dest="test_commit",
                         my_default=False, help="Commit database changes performed by YAML or XML tests.")
        parser.add_option_group(group)

        # Logging Group
        group = optparse.OptionGroup(parser, "Logging Configuration")
        group.add_option("--logfile", dest="logfile", help="file where the server log will be stored")
        group.add_option("--logrotate", dest="logrotate", action="store_true", my_default=False, help="enable logfile rotation")
        group.add_option("--syslog", action="store_true", dest="syslog", my_default=False, help="Send the log to the syslog server")
        group.add_option('--log-handler', action="append", default=[], my_default=DEFAULT_LOG_HANDLER, metavar="PREFIX:LEVEL", help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "odoo.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')
        group.add_option('--log-request', action="append_const", dest="log_handler", const="odoo.http.rpc.request:DEBUG", help='shortcut for --log-handler=odoo.http.rpc.request:DEBUG')
        group.add_option('--log-response', action="append_const", dest="log_handler", const="odoo.http.rpc.response:DEBUG", help='shortcut for --log-handler=odoo.http.rpc.response:DEBUG')
        group.add_option('--log-web', action="append_const", dest="log_handler", const="odoo.http:DEBUG", help='shortcut for --log-handler=odoo.http:DEBUG')
        group.add_option('--log-sql', action="append_const", dest="log_handler", const="odoo.sql_db:DEBUG", help='shortcut for --log-handler=odoo.sql_db:DEBUG')
        group.add_option('--log-db', dest='log_db', help="Logging database", my_default=False)
        group.add_option('--log-db-level', dest='log_db_level', my_default='warning', help="Logging database level")
        # For backward-compatibility, map the old log levels to something
        # quite close.
        levels = [
            'info', 'debug_rpc', 'warn', 'test', 'critical',
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
        group.add_option("--db_maxconn", dest="db_maxconn", type='int', my_default=64,
                         help="specify the the maximum number of physical connections to posgresql")
        group.add_option("--db-template", dest="db_template", my_default="template1",
                         help="specify a custom database template to create a new database")
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Internationalisation options",
            "Use these options to translate Odoo to another language."
            "See i18n section of the user manual. Option '-d' is mandatory."
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
                            help="disable the ability to return the list of databases")
        parser.add_option_group(security)

        # Advanced options
        group = optparse.OptionGroup(parser, "Advanced options")
        group.add_option('--dev', dest='dev_mode', type="string",
                         help="Enable developer mode. Param: List of options separated by comma. "
                              "Options : all, [pudb|wdb|ipdb|pdb], reload, qweb, werkzeug, xml")
        group.add_option('--shell-interface', dest='shell_interface', type="string",
                         help="Specify a preferred REPL to use in shell mode. Supported REPLs are: "
                              "[ipython|ptpython|bpython|python]")
        group.add_option("--stop-after-init", action="store_true", dest="stop_after_init", my_default=False,
                          help="stop the server after its initialization")
        group.add_option("--osv-memory-count-limit", dest="osv_memory_count_limit", my_default=False,
                         help="Force a limit on the maximum number of records kept in the virtual "
                              "osv_memory tables. The default is False, which means no count-based limit.",
                         type="int")
        group.add_option("--osv-memory-age-limit", dest="osv_memory_age_limit", my_default=1.0,
                         help="Force a limit on the maximum age of records kept in the virtual "
                              "osv_memory tables. This is a decimal value expressed in hours, "
                              "and the default is 1 hour.",
                         type="float")
        group.add_option("--max-cron-threads", dest="max_cron_threads", my_default=2,
                         help="Maximum number of threads processing concurrently cron jobs (default 2).",
                         type="int")
        group.add_option("--unaccent", dest="unaccent", my_default=False, action="store_true",
                         help="Use the unaccent function provided by the database when available.")
        group.add_option("--geoip-db", dest="geoip_database", my_default='/usr/share/GeoIP/GeoLiteCity.dat',
                         help="Absolute path to the GeoIP database file.")
        parser.add_option_group(group)

        if os.name == 'posix':
            group = optparse.OptionGroup(parser, "Multiprocessing options")
            # TODO sensible default for the three following limits.
            group.add_option("--workers", dest="workers", my_default=0,
                             help="Specify the number of workers, 0 disable prefork mode.",
                             type="int")
            group.add_option("--limit-memory-soft", dest="limit_memory_soft", my_default=2048 * 1024 * 1024,
                             help="Maximum allowed virtual memory per worker, when reached the worker be reset after the current request (default 671088640 aka 640MB).",
                             type="int")
            group.add_option("--limit-memory-hard", dest="limit_memory_hard", my_default=2560 * 1024 * 1024,
                             help="Maximum allowed virtual memory per worker, when reached, any memory allocation will fail (default 805306368 aka 768MB).",
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
            group.add_option("--limit-request", dest="limit_request", my_default=8192,
                             help="Maximum number of request to be processed per worker (default 8192).",
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
        former should be removed in the furture) with library-wide
        configuration values.

        This method must be called before proper usage of this library can be
        made.

        Typical usage of this method:

            odoo.tools.config.parse_config(sys.argv[1:])
        """
        self._parse_config(args)
        odoo.netsvc.init_logger()
        odoo.modules.module.initialize_sys_path()

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
                "them, preferrably '.odoorc'.")

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
        # and the server_wide_modules
        if self.options['server_wide_modules'] in ('', 'None', 'False'):
            self.options['server_wide_modules'] = 'web'

        # if defined dont take the configfile value even if the defined value is None
        keys = ['xmlrpc_interface', 'xmlrpc_port', 'longpolling_port',
                'db_name', 'db_user', 'db_password', 'db_host',
                'db_port', 'db_template', 'logfile', 'pidfile', 'smtp_port',
                'email_from', 'smtp_server', 'smtp_user', 'smtp_password',
                'db_maxconn', 'import_partial', 'addons_path',
                'xmlrpc', 'syslog', 'without_demo',
                'dbfilter', 'log_level', 'log_db',
                'log_db_level', 'geoip_database', 'dev_mode', 'shell_interface'
        ]

        for arg in keys:
            # Copy the command-line argument (except the special case for log_handler, due to
            # action=append requiring a real default, so we cannot use the my_default workaround)
            if getattr(opt, arg):
                self.options[arg] = getattr(opt, arg)
            # ... or keep, but cast, the config file value.
            elif isinstance(self.options[arg], basestring) and self.casts[arg].type in optparse.Option.TYPE_CHECKER:
                self.options[arg] = optparse.Option.TYPE_CHECKER[self.casts[arg].type](self.casts[arg], arg, self.options[arg])

        if isinstance(self.options['log_handler'], basestring):
            self.options['log_handler'] = self.options['log_handler'].split(',')
        self.options['log_handler'].extend(opt.log_handler)

        # if defined but None take the configfile value
        keys = [
            'language', 'translate_out', 'translate_in', 'overwrite_existing_translations',
            'dev_mode', 'shell_interface', 'smtp_ssl', 'load_language',
            'stop_after_init', 'logrotate', 'without_demo', 'xmlrpc', 'syslog',
            'list_db', 'proxy_mode',
            'test_file', 'test_enable', 'test_commit', 'test_report_directory',
            'osv_memory_count_limit', 'osv_memory_age_limit', 'max_cron_threads', 'unaccent',
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
            elif isinstance(self.options[arg], basestring) and self.casts[arg].type in optparse.Option.TYPE_CHECKER:
                self.options[arg] = optparse.Option.TYPE_CHECKER[self.casts[arg].type](self.casts[arg], arg, self.options[arg])

        self.options['root_path'] = os.path.abspath(os.path.expanduser(os.path.expandvars(os.path.join(os.path.dirname(__file__), '..'))))
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
                    os.path.abspath(os.path.expanduser(os.path.expandvars(x.strip())))
                      for x in self.options['addons_path'].split(','))

        self.options['init'] = opt.init and dict.fromkeys(opt.init.split(','), 1) or {}
        self.options['demo'] = (dict(self.options['init'])
                                if not self.options['without_demo'] else {})
        self.options['update'] = opt.update and dict.fromkeys(opt.update.split(','), 1) or {}
        self.options['translate_modules'] = opt.translate_modules and [m.strip() for m in opt.translate_modules.split(',')] or ['all']
        self.options['translate_modules'].sort()

        dev_split = opt.dev_mode and  [s.strip() for s in opt.dev_mode.split(',')] or []
        self.options['dev_mode'] = 'all' in dev_split and dev_split + ['pdb', 'reload', 'qweb', 'werkzeug', 'xml'] or dev_split

        if opt.pg_path:
            self.options['pg_path'] = opt.pg_path

        if self.options.get('language', False):
            if len(self.options['language']) > 5:
                raise Exception('ERROR: The Lang name must take max 5 chars, Eg: -lfr_BE')

        if opt.save:
            self.save()

        odoo.conf.addons_paths = self.options['addons_path'].split(',')

        odoo.conf.server_wide_modules = [
            m.strip() for m in self.options['server_wide_modules'].split(',') if m.strip()
        ]

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
                raise optparse.OptionValueError("option %s: no such directory: %r" % (opt, path))
            if not self._is_addons_path(res):
                raise optparse.OptionValueError("option %s: The addons-path %r does not seem to a be a valid Addons Directory!" % (opt, path))
            ad_paths.append(res)

        setattr(parser.values, option.dest, ",".join(ad_paths))

    def load(self):
        p = ConfigParser.ConfigParser()
        try:
            p.read([self.rcfile])
            for (name,value) in p.items('options'):
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

    def save(self):
        p = ConfigParser.ConfigParser()
        loglevelnames = dict(pycompat.izip(pycompat.values(self._LOGLEVELS), pycompat.keys(self._LOGLEVELS)))
        p.add_section('options')
        for opt in sorted(pycompat.keys(self.options)):
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

        for sec in sorted(pycompat.keys(self.misc)):
            p.add_section(sec)
            for opt in sorted(pycompat.keys(self.misc[sec])):
                p.set(sec,opt,self.misc[sec][opt])

        # try to create the directories and write the file
        try:
            rc_exists = os.path.exists(self.rcfile)
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
        if key in self.options and isinstance(self.options[key], basestring) and \
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
        if not os.path.exists(d):
            os.makedirs(d, 0o700)
        else:
            assert os.access(d, os.W_OK), \
                "%s: directory is not writable" % d
        return d

    def filestore(self, dbname):
        return os.path.join(self['data_dir'], 'filestore', dbname)

config = configmanager()
