#openerp.loggers.handlers. -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2014 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import ConfigParser
import optparse
import os
import sys
import openerp
import openerp.conf
import openerp.loglevels as loglevels
import logging
import openerp.release as release
import appdirs

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

def _check_ssl():
    try:
        from OpenSSL import SSL
        import socket

        return hasattr(socket, 'ssl') and hasattr(SSL, "Connection")
    except:
        return False

def _get_default_datadir():
    home = os.path.expanduser('~')
    if os.path.exists(home):
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
    if for some odd reason people use :option`odoo.py --save`` all the time.
    """
    # dict(iterable) -> the last item of iterable for any given key wins,
    # which is what we want and expect. Output order should not matter as
    # there are no duplicates within the output sequence
    return (
        '{}:{}'.format(logger, level)
        for logger, level in dict(it.split(':') for it in loggers).iteritems()
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
            'init', 'save', 'config', 'update', 'stop_after_init'
        ])

        # dictionary mapping option destination (keys in self.options) to MyOptions.
        self.casts = {}

        self.misc = {}
        self.config_file = fname
        self.has_ssl = _check_ssl()

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
                          help="save configuration to ~/.openerp_serverrc")
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
        group.add_option("--load", dest="server_wide_modules", help="Comma-separated list of server-wide modules default=web")

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

        # XML-RPC / HTTPS
        title = "XML-RPC Secure Configuration"
        if not self.has_ssl:
            title += " (disabled as ssl is unavailable)"

        group = optparse.OptionGroup(parser, title)
        group.add_option("--xmlrpcs-interface", dest="xmlrpcs_interface", my_default='',
                         help="Specify the TCP IP address for the XML-RPC Secure protocol. The empty string binds to all interfaces.")
        group.add_option("--xmlrpcs-port", dest="xmlrpcs_port", my_default=8071,
                         help="specify the TCP port for the XML-RPC Secure protocol", type="int")
        group.add_option("--no-xmlrpcs", dest="xmlrpcs", action="store_false", my_default=True,
                         help="disable the XML-RPC Secure protocol")
        group.add_option("--cert-file", dest="secure_cert_file", my_default='server.cert',
                         help="specify the certificate file for the SSL connection")
        group.add_option("--pkey-file", dest="secure_pkey_file", my_default='server.pkey',
                         help="specify the private key file for the SSL connection")
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
        group.add_option('--log-handler', action="append", default=[], my_default=DEFAULT_LOG_HANDLER, metavar="PREFIX:LEVEL", help='setup a handler at LEVEL for a given PREFIX. An empty PREFIX indicates the root logger. This option can be repeated. Example: "openerp.orm:DEBUG" or "werkzeug:CRITICAL" (default: ":INFO")')
        group.add_option('--log-request', action="append_const", dest="log_handler", const="openerp.http.rpc.request:DEBUG", help='shortcut for --log-handler=openerp.http.rpc.request:DEBUG')
        group.add_option('--log-response', action="append_const", dest="log_handler", const="openerp.http.rpc.response:DEBUG", help='shortcut for --log-handler=openerp.http.rpc.response:DEBUG')
        group.add_option('--log-web', action="append_const", dest="log_handler", const="openerp.http:DEBUG", help='shortcut for --log-handler=openerp.http:DEBUG')
        group.add_option('--log-sql', action="append_const", dest="log_handler", const="openerp.sql_db:DEBUG", help='shortcut for --log-handler=openerp.sql_db:DEBUG')
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
        if os.name == 'posix':
            group.add_option('--auto-reload', dest='auto_reload', action='store_true', my_default=False, help='enable auto reload')
        group.add_option('--debug', dest='debug_mode', action='store_true', my_default=False, help='enable debug mode')
        group.add_option("--stop-after-init", action="store_true", dest="stop_after_init", my_default=False,
                          help="stop the server after its initialization")
        group.add_option("-t", "--timezone", dest="timezone", my_default=False,
                         help="specify reference timezone for the server (e.g. Europe/Brussels")
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

        This method initializes openerp.tools.config and openerp.conf (the
        former should be removed in the furture) with library-wide
        configuration values.

        This method must be called before proper usage of this library can be
        made.

        Typical usage of this method:

            openerp.tools.config.parse_config(sys.argv[1:])
        """
        self._parse_config(args)
        openerp.netsvc.init_logger()
        openerp.modules.module.initialize_sys_path()

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
            rcfilepath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'openerp-server.conf')
        else:
            rcfilepath = os.path.expanduser('~/.openerp_serverrc')

        self.rcfile = os.path.abspath(
            self.config_file or opt.config or os.environ.get('OPENERP_SERVER') or rcfilepath)
        self.load()

        # Verify that we want to log or not, if not the output will go to stdout
        if self.options['logfile'] in ('None', 'False'):
            self.options['logfile'] = False
        # the same for the pidfile
        if self.options['pidfile'] in ('None', 'False'):
            self.options['pidfile'] = False

        # if defined dont take the configfile value even if the defined value is None
        keys = ['xmlrpc_interface', 'xmlrpc_port', 'longpolling_port',
                'db_name', 'db_user', 'db_password', 'db_host',
                'db_port', 'db_template', 'logfile', 'pidfile', 'smtp_port',
                'email_from', 'smtp_server', 'smtp_user', 'smtp_password',
                'db_maxconn', 'import_partial', 'addons_path',
                'xmlrpc', 'syslog', 'without_demo', 'timezone',
                'xmlrpcs_interface', 'xmlrpcs_port', 'xmlrpcs',
                'secure_cert_file', 'secure_pkey_file', 'dbfilter', 'log_level', 'log_db',
                'log_db_level', 'geoip_database',
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
            'debug_mode', 'smtp_ssl', 'load_language',
            'stop_after_init', 'logrotate', 'without_demo', 'xmlrpc', 'syslog',
            'list_db', 'xmlrpcs', 'proxy_mode',
            'test_file', 'test_enable', 'test_commit', 'test_report_directory',
            'osv_memory_count_limit', 'osv_memory_age_limit', 'max_cron_threads', 'unaccent',
            'data_dir',
        ]

        posix_keys = [
            'auto_reload', 'workers',
            'limit_memory_hard', 'limit_memory_soft',
            'limit_time_cpu', 'limit_time_real', 'limit_request',
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

        self.options['root_path'] = os.path.abspath(os.path.expanduser(os.path.expandvars(os.path.dirname(openerp.__file__))))
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
                    os.path.abspath(os.path.expanduser(os.path.expandvars(x)))
                      for x in self.options['addons_path'].split(','))

        self.options['init'] = opt.init and dict.fromkeys(opt.init.split(','), 1) or {}
        self.options['demo'] = not opt.without_demo and dict(self.options['init']) or {}
        self.options['update'] = opt.update and dict.fromkeys(opt.update.split(','), 1) or {}
        self.options['translate_modules'] = opt.translate_modules and map(lambda m: m.strip(), opt.translate_modules.split(',')) or ['all']
        self.options['translate_modules'].sort()

        # TODO checking the type of the parameters should be done for every
        # parameters, not just the timezone.
        # The call to get_server_timezone() sets the timezone; this should
        # probably done here.
        if self.options['timezone']:
            # Prevent the timezone to be True. (The config file parsing changes
            # the string 'True' to the boolean value True. It would be probably
            # be better to remove that conversion.)
            die(not isinstance(self.options['timezone'], basestring),
                "Invalid timezone value in configuration or environment: %r.\n"
                "Please fix this in your configuration." %(self.options['timezone']))

            # If an explicit TZ was provided in the config, make sure it is known
            try:
                import pytz
                pytz.timezone(self.options['timezone'])
            except pytz.UnknownTimeZoneError:
                die(True, "The specified timezone (%s) is invalid" % self.options['timezone'])
            except:
                # If pytz is missing, don't check the provided TZ, it will be ignored anyway.
                pass

        if opt.pg_path:
            self.options['pg_path'] = opt.pg_path

        if self.options.get('language', False):
            if len(self.options['language']) > 5:
                raise Exception('ERROR: The Lang name must take max 5 chars, Eg: -lfr_BE')

        if not self.options['db_user']:
            try:
                import getpass
                self.options['db_user'] = getpass.getuser()
            except:
                self.options['db_user'] = None

        die(not self.options['db_user'], 'ERROR: No user specified for the connection to the database')

        if self.options['db_password']:
            if sys.platform == 'win32' and not self.options['db_host']:
                self.options['db_host'] = 'localhost'
            #if self.options['db_host']:
            #    self._generate_pgpassfile()

        if opt.save:
            self.save()

        openerp.conf.addons_paths = self.options['addons_path'].split(',')
        if opt.server_wide_modules:
            openerp.conf.server_wide_modules = map(lambda m: m.strip(), opt.server_wide_modules.split(','))
        else:
            openerp.conf.server_wide_modules = ['web','web_kanban']

    def _generate_pgpassfile(self):
        """
        Generate the pgpass file with the parameters from the command line (db_host, db_user,
        db_password)

        Used because pg_dump and pg_restore can not accept the password on the command line.
        """
        is_win32 = sys.platform == 'win32'
        if is_win32:
            filename = os.path.join(os.environ['APPDATA'], 'pgpass.conf')
        else:
            filename = os.path.join(os.environ['HOME'], '.pgpass')

        text_to_add = "%(db_host)s:*:*:%(db_user)s:%(db_password)s" % self.options

        if os.path.exists(filename):
            content = [x.strip() for x in file(filename, 'r').readlines()]
            if text_to_add in content:
                return

        fp = file(filename, 'a+')
        fp.write(text_to_add + "\n")
        fp.close()

        if is_win32:
            try:
                import _winreg
            except ImportError:
                _winreg = None
            x=_winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
            y = _winreg.OpenKey(x, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0,_winreg.KEY_ALL_ACCESS)
            _winreg.SetValueEx(y,"PGPASSFILE", 0, _winreg.REG_EXPAND_SZ, filename )
            _winreg.CloseKey(y)
            _winreg.CloseKey(x)
        else:
            import stat
            os.chmod(filename, stat.S_IRUSR + stat.S_IWUSR)

    def _is_addons_path(self, path):
        for f in os.listdir(path):
            modpath = os.path.join(path, f)
            if os.path.isdir(modpath):
                def hasfile(filename):
                    return os.path.isfile(os.path.join(modpath, filename))
                if hasfile('__init__.py') and (hasfile('__openerp__.py') or hasfile('__terp__.py')):
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
                if not self.misc.has_key(sec):
                    self.misc[sec]= {}
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
        loglevelnames = dict(zip(self._LOGLEVELS.values(), self._LOGLEVELS.keys()))
        p.add_section('options')
        for opt in sorted(self.options.keys()):
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

        for sec in sorted(self.misc.keys()):
            p.add_section(sec)
            for opt in sorted(self.misc[sec].keys()):
                p.set(sec,opt,self.misc[sec][opt])

        # try to create the directories and write the file
        try:
            rc_exists = os.path.exists(self.rcfile)
            if not rc_exists and not os.path.exists(os.path.dirname(self.rcfile)):
                os.makedirs(os.path.dirname(self.rcfile))
            try:
                p.write(file(self.rcfile, 'w'))
                if not rc_exists:
                    os.chmod(self.rcfile, 0600)
            except IOError:
                sys.stderr.write("ERROR: couldn't write the config file\n")

        except OSError:
            # what to do if impossible?
            sys.stderr.write("ERROR: couldn't create the config directory\n")

    def get(self, key, default=None):
        return self.options.get(key, default)

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
        d = os.path.join(self['data_dir'], 'addons', release.series)
        if not os.path.exists(d):
            os.makedirs(d, 0700)
        else:
            assert os.access(d, os.W_OK), \
                "%s: directory is not writable" % d
        return d

    @property
    def session_dir(self):
        d = os.path.join(self['data_dir'], 'sessions')
        if not os.path.exists(d):
            os.makedirs(d, 0700)
        else:
            assert os.access(d, os.W_OK), \
                "%s: directory is not writable" % d
        return d

    def filestore(self, dbname):
        return os.path.join(self['data_dir'], 'filestore', dbname)

config = configmanager()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
