# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

#.apidoc title: Server Configuration Loader

def check_ssl():
    try:
        from OpenSSL import SSL
        import socket

        return hasattr(socket, 'ssl') and hasattr(SSL, "Connection")
    except:
        return False

class configmanager(object):
    def __init__(self, fname=None):
        # Options not exposed on the command line. Command line options will be added
        # from optparse's parser.
        self.options = {
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'login_message': False,
            'publisher_warranty_url': 'http://services.openerp.com/publisher-warranty/',
            'reportgz': False,
            'root_path': None,
        }

        # Not exposed in the configuration file.
        self.blacklist_for_save = set(
            ['publisher_warranty_url', 'load_language', 'root_path',
            'init', 'save', 'config', 'update'])

        # dictionary mapping option destination (keys in self.options) to MyOptions.
        self.casts = {}

        self.misc = {}
        self.config_file = fname
        self.has_ssl = check_ssl()

        self._LOGLEVELS = dict([(getattr(loglevels, 'LOG_%s' % x), getattr(logging, x))
                          for x in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'TEST', 'DEBUG', 'DEBUG_RPC', 'DEBUG_SQL', 'DEBUG_RPC_ANSWER','NOTSET')])

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
        group.add_option("--load", dest="server_wide_modules", help="Comma-separated list of server-wide modules")
        parser.add_option_group(group)

        # XML-RPC / HTTP
        group = optparse.OptionGroup(parser, "XML-RPC Configuration")
        group.add_option("--xmlrpc-interface", dest="xmlrpc_interface", my_default='',
                         help="Specify the TCP IP address for the XML-RPC protocol. The empty string binds to all interfaces.")
        group.add_option("--xmlrpc-port", dest="xmlrpc_port", my_default=8069,
                         help="specify the TCP port for the XML-RPC protocol", type="int")
        group.add_option("--no-xmlrpc", dest="xmlrpc", action="store_false", my_default=True,
                         help="disable the XML-RPC protocol")
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

        # NET-RPC
        group = optparse.OptionGroup(parser, "NET-RPC Configuration")
        group.add_option("--netrpc-interface", dest="netrpc_interface", my_default='',
                         help="specify the TCP IP address for the NETRPC protocol")
        group.add_option("--netrpc-port", dest="netrpc_port", my_default=8070,
                         help="specify the TCP port for the NETRPC protocol", type="int")
        group.add_option("--no-netrpc", dest="netrpc", action="store_false", my_default=True,
                         help="disable the NETRPC protocol")
        parser.add_option_group(group)

        # WEB
        # TODO move to web addons after MetaOption merge
        group = optparse.OptionGroup(parser, "Web interface Configuration")
        group.add_option("--db-filter", dest="dbfilter", default='.*',
                         help="Filter listed database", metavar="REGEXP")
        parser.add_option_group(group)

        # Static HTTP
        group = optparse.OptionGroup(parser, "Static HTTP service")
        group.add_option("--static-http-enable", dest="static_http_enable", action="store_true", my_default=False, help="enable static HTTP service for serving plain HTML files")
        group.add_option("--static-http-document-root", dest="static_http_document_root", help="specify the directory containing your static HTML files (e.g '/var/www/')")
        group.add_option("--static-http-url-prefix", dest="static_http_url_prefix", help="specify the URL root prefix where you want web browsers to access your static HTML files (e.g '/')")
        parser.add_option_group(group)

        # Testing Group
        group = optparse.OptionGroup(parser, "Testing Configuration")
        group.add_option("--test-file", dest="test_file", my_default=False,
                         help="Launch a YML test file.")
        group.add_option("--test-report-directory", dest="test_report_directory", my_default=False,
                         help="If set, will save sample of all reports in this directory.")
        group.add_option("--test-disable", action="store_true", dest="test_disable",
                         my_default=False, help="Disable loading test files.")
        group.add_option("--test-commit", action="store_true", dest="test_commit",
                         my_default=False, help="Commit database changes performed by tests.")
        group.add_option("--assert-exit-level", dest='assert_exit_level', type="choice", choices=self._LOGLEVELS.keys(),
                         my_default='error',
                         help="specify the level at which a failed assertion will stop the server. Accepted values: %s" % (self._LOGLEVELS.keys(),))
        parser.add_option_group(group)

        # Logging Group
        group = optparse.OptionGroup(parser, "Logging Configuration")
        group.add_option("--logfile", dest="logfile", help="file where the server log will be stored")
        group.add_option("--no-logrotate", dest="logrotate", action="store_false", my_default=True,
                         help="do not rotate the logfile")
        group.add_option("--syslog", action="store_true", dest="syslog",
                         my_default=False, help="Send the log to the syslog server")
        group.add_option('--log-level', dest='log_level', type='choice', choices=self._LOGLEVELS.keys(),
                         my_default='info',
                         help='specify the level of the logging. Accepted values: ' + str(self._LOGLEVELS.keys()))
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
                         help='specify the SMTP server support SSL or not')
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
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Internationalisation options",
            "Use these options to translate OpenERP to another language."
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
        group.add_option("--addons-path", dest="addons_path",
                         help="specify additional addons paths (separated by commas).",
                         action="callback", callback=self._check_addons_path, nargs=1, type="string")
        parser.add_option_group(group)

        security = optparse.OptionGroup(parser, 'Security-related options')
        security.add_option('--no-database-list', action="store_false", dest='list_db', my_default=True,
                            help="disable the ability to return the list of databases")
        parser.add_option_group(security)

        # Advanced options
        group = optparse.OptionGroup(parser, "Advanced options")
        group.add_option("--cache-timeout", dest="cache_timeout", my_default=100000,
                          help="set the timeout for the cache system", type="int")
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
        group.add_option("--max-cron-threads", dest="max_cron_threads", my_default=4,
                         help="Maximum number of threads processing concurrently cron jobs.",
                         type="int")
        group.add_option("--unaccent", dest="unaccent", my_default=False, action="store_true",
                         help="Use the unaccent function provided by the database when available.")

        parser.add_option_group(group)

        # Copy all optparse options (i.e. MyOption) into self.options.
        for group in parser.option_groups:
            for option in group.option_list:
                self.options[option.dest] = option.my_default
                self.casts[option.dest] = option

        self.parse_config(None, False)

    def parse_config(self, args=None, complete=True):
        """ Parse the configuration file (if any) and the command-line
        arguments.

        This method initializes openerp.tools.config and openerp.conf (the
        former should be removed in the furture) with library-wide
        configuration values.

        This method must be called before proper usage of this library can be
        made.

        Typical usage of this method:

            openerp.tools.config.parse_config(sys.argv[1:])

        :param complete: this is a hack used in __init__(), leave it to True.

        """
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
        die(not opt.save and opt.config and not os.path.exists(opt.config),
            "The config file '%s' selected with -c/--config doesn't exist, "\
            "use -s/--save if you want to generate it"%(opt.config))

        # place/search the config file on Win32 near the server installation
        # (../etc from the server)
        # if the server is run by an unprivileged user, he has to specify location of a config file where he has the rights to write,
        # else he won't be able to save the configurations, or even to start the server...
        if os.name == 'nt':
            rcfilepath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'openerp-server.conf')
        else:
            rcfilepath = os.path.expanduser('~/.openerp_serverrc')

        self.rcfile = os.path.abspath(
            self.config_file or opt.config \
                or os.environ.get('OPENERP_SERVER') or rcfilepath)
        self.load()


        # Verify that we want to log or not, if not the output will go to stdout
        if self.options['logfile'] in ('None', 'False'):
            self.options['logfile'] = False
        # the same for the pidfile
        if self.options['pidfile'] in ('None', 'False'):
            self.options['pidfile'] = False

        keys = ['xmlrpc_interface', 'xmlrpc_port', 'db_name', 'db_user', 'db_password', 'db_host',
                'db_port', 'logfile', 'pidfile', 'smtp_port', 'cache_timeout',
                'email_from', 'smtp_server', 'smtp_user', 'smtp_password',
                'netrpc_interface', 'netrpc_port', 'db_maxconn', 'import_partial', 'addons_path',
                'netrpc', 'xmlrpc', 'syslog', 'without_demo', 'timezone',
                'xmlrpcs_interface', 'xmlrpcs_port', 'xmlrpcs',
                'static_http_enable', 'static_http_document_root', 'static_http_url_prefix',
                'secure_cert_file', 'secure_pkey_file', 'dbfilter'
                ]

        for arg in keys:
            # Copy the command-line argument...
            if getattr(opt, arg):
                self.options[arg] = getattr(opt, arg)
            # ... or keep, but cast, the config file value.
            elif isinstance(self.options[arg], basestring) and self.casts[arg].type in optparse.Option.TYPE_CHECKER:
                self.options[arg] = optparse.Option.TYPE_CHECKER[self.casts[arg].type](self.casts[arg], arg, self.options[arg])

        keys = [
            'language', 'translate_out', 'translate_in', 'overwrite_existing_translations',
            'debug_mode', 'smtp_ssl', 'load_language',
            'stop_after_init', 'logrotate', 'without_demo', 'netrpc', 'xmlrpc', 'syslog',
            'list_db', 'xmlrpcs',
            'test_file', 'test_disable', 'test_commit', 'test_report_directory',
            'osv_memory_count_limit', 'osv_memory_age_limit', 'max_cron_threads', 'unaccent',
        ]

        for arg in keys:
            # Copy the command-line argument...
            if getattr(opt, arg) is not None:
                self.options[arg] = getattr(opt, arg)
            # ... or keep, but cast, the config file value.
            elif isinstance(self.options[arg], basestring) and self.casts[arg].type in optparse.Option.TYPE_CHECKER:
                self.options[arg] = optparse.Option.TYPE_CHECKER[self.casts[arg].type](self.casts[arg], arg, self.options[arg])

        if opt.assert_exit_level:
            self.options['assert_exit_level'] = self._LOGLEVELS[opt.assert_exit_level]
        else:
            self.options['assert_exit_level'] = self._LOGLEVELS.get(self.options['assert_exit_level']) or int(self.options['assert_exit_level'])

        if opt.log_level:
            self.options['log_level'] = self._LOGLEVELS[opt.log_level]
        else:
            self.options['log_level'] = self._LOGLEVELS.get(self.options['log_level']) or int(self.options['log_level'])

        self.options['root_path'] = os.path.abspath(os.path.expanduser(os.path.expandvars(os.path.dirname(openerp.__file__))))
        if not self.options['addons_path'] or self.options['addons_path']=='None':
            self.options['addons_path'] = os.path.join(self.options['root_path'], 'addons')
        else:
            self.options['addons_path'] = ",".join(
                    os.path.abspath(os.path.expanduser(os.path.expandvars(x)))
                      for x in self.options['addons_path'].split(','))

        self.options['init'] = opt.init and dict.fromkeys(opt.init.split(','), 1) or {}
        self.options["demo"] = not opt.without_demo and self.options['init'] or {}
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

        openerp.conf.max_cron_threads = self.options['max_cron_threads']

        openerp.conf.addons_paths = self.options['addons_path'].split(',')
        openerp.conf.server_wide_modules = \
            map(lambda m: m.strip(), opt.server_wide_modules.split(',')) if \
            opt.server_wide_modules else []
        if complete:
            openerp.modules.module.initialize_sys_path()
            openerp.modules.loading.open_openerp_namespace()
            # openerp.addons.__path__.extend(openerp.conf.addons_paths) # This
            # is not compatible with initialize_sys_path(): import crm and
            # import openerp.addons.crm load twice the module.

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
            if opt in ('log_level', 'assert_exit_level'):
                p.set('options', opt, loglevelnames.get(self.options[opt], self.options[opt]))
            else:
                p.set('options', opt, self.options[opt])

        for sec in sorted(self.misc.keys()):
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

    def __getitem__(self, key):
        return self.options[key]

config = configmanager()

