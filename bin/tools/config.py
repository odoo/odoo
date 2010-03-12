# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import ConfigParser
import optparse
import os
import sys
import netsvc
import logging
import release

def check_ssl():
    try:
        from OpenSSL import SSL
        import socket

        return hasattr(socket, 'ssl')
    except:
        return False

class configmanager(object):
    def __init__(self, fname=None):
        self.options = {
            'email_from':False,
            'interface': '',    # this will bind the server to all interfaces
            'port': 8069,
            'netinterface': '',
            'netport': 8070,
            'db_host': False,
            'db_port': False,
            'db_name': False,
            'db_user': False,
            'db_password': False,
            'db_maxconn': 64,
            'reportgz': False,
            'netrpc': True,
            'xmlrpc': True,
            'soap': False,
            'translate_in': None,
            'translate_out': None,
            'language': None,
            'pg_path': None,
            'admin_passwd': 'admin',
            'csv_internal_sep': ',',
            'addons_path': None,
            'root_path': None,
            'debug_mode': False,
            'import_partial': "",
            'pidfile': None,
            'logfile': None,
            'smtp_server': 'localhost',
            'smtp_user': False,
            'smtp_port':25,
            'smtp_password': False,
            'stop_after_init': False,   # this will stop the server after initialization
            'price_accuracy': 2,
            'secure' : False,
            'syslog' : False,
            'log_level': logging.INFO,
            'assert_exit_level': logging.WARNING, # level above which a failed assert will be raise
            'cache_timeout': 100000,
            'login_message': False,
            'list_db': True,
        }

        hasSSL = check_ssl()

        self._LOGLEVELS = dict([(getattr(netsvc, 'LOG_%s' % x), getattr(logging, x))
                          for x in ('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'DEBUG_RPC', 'NOTSET')])

        version = "%s %s" % (release.description, release.version)
        parser = optparse.OptionParser(version=version)

        parser.add_option("-c", "--config", dest="config", help="specify alternate config file")
        parser.add_option("-s", "--save", action="store_true", dest="save", default=False,
                          help="save configuration to ~/.openerp_serverrc")
        parser.add_option("--pidfile", dest="pidfile", help="file where the server pid will be stored")

        parser.add_option("-n", "--interface", dest="interface", help="specify the TCP IP address")
        parser.add_option("-p", "--port", dest="port", help="specify the TCP port", type="int")
        parser.add_option("--net_interface", dest="netinterface", help="specify the TCP IP address for netrpc")
        parser.add_option("--net_port", dest="netport", help="specify the TCP port for netrpc", type="int")
        parser.add_option("--no-netrpc", dest="netrpc", action="store_false", default=True, help="disable netrpc")
        parser.add_option("--no-xmlrpc", dest="xmlrpc", action="store_false", default=True, help="disable xmlrpc")
        parser.add_option("-i", "--init", dest="init", help="init a module (use \"all\" for all modules)")
        parser.add_option("--without-demo", dest="without_demo",
                          help="load demo data for a module (use \"all\" for all modules)", default=False)
        parser.add_option("-u", "--update", dest="update",
                          help="update a module (use \"all\" for all modules)")
        parser.add_option("--cache-timeout", dest="cache_timeout",
                          help="set the timeout for the cache system", default=100000, type="int")

        # stops the server from launching after initialization
        parser.add_option("--stop-after-init", action="store_true", dest="stop_after_init", default=False,
                          help="stop the server after it initializes")
        parser.add_option('--debug', dest='debug_mode', action='store_true', default=False, help='enable debug mode')
        parser.add_option("--assert-exit-level", dest='assert_exit_level', type="choice", choices=self._LOGLEVELS.keys(),
                          help="specify the level at which a failed assertion will stop the server. Accepted values: %s" % (self._LOGLEVELS.keys(),))
        parser.add_option('--price_accuracy', dest='price_accuracy', default='2', help='specify the price accuracy')

        if hasSSL:
            group = optparse.OptionGroup(parser, "SSL Configuration")
            group.add_option("-S", "--secure", dest="secure",
                             help="launch server over https instead of http")
            group.add_option("--cert-file", dest="secure_cert_file",
                              default="server.cert",
                              help="specify the certificate file for the SSL connection")
            group.add_option("--pkey-file", dest="secure_pkey_file",
                              default="server.pkey",
                              help="specify the private key file for the SSL connection")
            parser.add_option_group(group)

        # Logging Group
        group = optparse.OptionGroup(parser, "Logging Configuration")
        group.add_option("--logfile", dest="logfile", help="file where the server log will be stored")
        group.add_option("--syslog", action="store_true", dest="syslog",
                         default=False, help="Send the log to the syslog server")
        group.add_option('--log-level', dest='log_level', type='choice', choices=self._LOGLEVELS.keys(),
                         help='specify the level of the logging. Accepted values: ' + str(self._LOGLEVELS.keys()))
        parser.add_option_group(group)

        # SMTP Group
        group = optparse.OptionGroup(parser, "SMTP Configuration")
        group.add_option('--email-from', dest='email_from', default='', help='specify the SMTP email address for sending email')
        group.add_option('--smtp', dest='smtp_server', default='', help='specify the SMTP server for sending email')
        group.add_option('--smtp-port', dest='smtp_port', default='25', help='specify the SMTP port', type="int")
        group.add_option('--smtp-ssl', dest='smtp_ssl', default='', help='specify the SMTP server support SSL or not')
        group.add_option('--smtp-user', dest='smtp_user', default='', help='specify the SMTP username for sending email')
        group.add_option('--smtp-password', dest='smtp_password', default='', help='specify the SMTP password for sending email')
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Database related options")
        group.add_option("-d", "--database", dest="db_name", help="specify the database name")
        group.add_option("-r", "--db_user", dest="db_user", help="specify the database user name")
        group.add_option("-w", "--db_password", dest="db_password", help="specify the database password")
        group.add_option("--pg_path", dest="pg_path", help="specify the pg executable path")
        group.add_option("--db_host", dest="db_host", help="specify the database host")
        group.add_option("--db_port", dest="db_port", help="specify the database port", type="int")
        group.add_option("--db_maxconn", dest="db_maxconn", default='64',
                         help="specify the the maximum number of physical connections to posgresql")
        group.add_option("-P", "--import-partial", dest="import_partial",
                         help="Use this for big data importation, if it crashes you will be able to continue at the current state. Provide a filename to store intermediate importation states.", default=False)
        parser.add_option_group(group)

        group = optparse.OptionGroup(parser, "Internationalisation options",
            "Use these options to translate OpenERP to another language."
            "See i18n section of the user manual. Option '-d' is mandatory."
            "Option '-l' is mandatory in case of importation"
            )

        group.add_option('-l', "--language", dest="language",
                         help="specify the language of the translation file. Use it with --i18n-export or --i18n-import")
        group.add_option("--i18n-export", dest="translate_out",
                         help="export all sentences to be translated to a CSV file, a PO file or a TGZ archive and exit")
        group.add_option("--i18n-import", dest="translate_in",
                         help="import a CSV or a PO file with translations and exit. The '-l' option is required.")
        group.add_option("--modules", dest="translate_modules",
                         help="specify modules to export. Use in combination with --i18n-export")
        group.add_option("--addons-path", dest="addons_path",
                         help="specify an alternative addons path.",
                         action="callback", callback=self._check_addons_path, nargs=1, type="string")
        parser.add_option_group(group)

        security = optparse.OptionGroup(parser, 'Security-related options')
        security.add_option('--no-database-list', action="store_false", dest='list_db', default=True, help="disable the ability to return the list of databases")
        security.add_option('--enable-code-actions', action='store_true',
                            dest='server_actions_allow_code', default=False,
                            help='Enables server actions of state "code". Warning, this is a security risk.')
        parser.add_option_group(security)

        (opt, args) = parser.parse_args()

        def die(cond, msg):
            if cond:
                print msg
                sys.exit(1)

        die(bool(opt.syslog) and bool(opt.logfile),
            "the syslog and logfile options are exclusive")

        die(opt.translate_in and (not opt.language or not opt.db_name),
            "the i18n-import option cannot be used without the language (-l) and the database (-d) options")

        die(opt.translate_out and (not opt.db_name),
            "the i18n-export option cannot be used without the database (-d) option")

        # place/search the config file on Win32 near the server installation
        # (../etc from the server)
        # if the server is run by an unprivileged user, he has to specify location of a config file where he has the rights to write,
        # else he won't be able to save the configurations, or even to start the server...
        if os.name == 'nt':
            rcfilepath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), 'openerp-server.conf')
        else:
            rcfilepath = os.path.expanduser('~/.openerp_serverrc')

        self.rcfile = os.path.abspath(
            fname or opt.config or os.environ.get('OPENERP_SERVER') or rcfilepath)
        self.load()


        # Verify that we want to log or not, if not the output will go to stdout
        if self.options['logfile'] in ('None', 'False'):
            self.options['logfile'] = False
        # the same for the pidfile
        if self.options['pidfile'] in ('None', 'False'):
            self.options['pidfile'] = False

        keys = ['interface', 'port', 'db_name', 'db_user', 'db_password', 'db_host',
                'db_port', 'logfile', 'pidfile', 'smtp_port', 'cache_timeout', 'smtp_ssl', 
                'email_from', 'smtp_server', 'smtp_user', 'smtp_password', 'price_accuracy',
                'netinterface', 'netport', 'db_maxconn', 'import_partial', 'addons_path']

        if hasSSL:
            keys.extend(['smtp_ssl', 'secure_cert_file', 'secure_pkey_file'])

        for arg in keys:
            if getattr(opt, arg):
                self.options[arg] = getattr(opt, arg)

        keys = ['language', 'translate_out', 'translate_in', 'debug_mode',
                'stop_after_init', 'without_demo', 'netrpc', 'xmlrpc', 'syslog',
                'list_db', 'server_actions_allow_code']

        if hasSSL and not  self.options['secure']:
            keys.append('secure')

        for arg in keys:
            if getattr(opt, arg) is not None:
                self.options[arg] = getattr(opt, arg)

        if opt.assert_exit_level:
            self.options['assert_exit_level'] = self._LOGLEVELS[opt.assert_exit_level]
        else:
            self.options['assert_exit_level'] = self._LOGLEVELS.get(self.options['assert_exit_level']) or int(self.options['assert_exit_level'])

        if opt.log_level:
            self.options['log_level'] = self._LOGLEVELS[opt.log_level]
        else:
            self.options['log_level'] = self._LOGLEVELS.get(self.options['log_level']) or int(self.options['log_level'])

        if not self.options['root_path'] or self.options['root_path']=='None':
            self.options['root_path'] = os.path.abspath(os.path.dirname(sys.argv[0]))
        if not self.options['addons_path'] or self.options['addons_path']=='None':
            self.options['addons_path'] = os.path.join(self.options['root_path'], 'addons')

        self.options['init'] = opt.init and dict.fromkeys(opt.init.split(','), 1) or {}
        self.options["demo"] = not opt.without_demo and self.options['init'] or {}
        self.options['update'] = opt.update and dict.fromkeys(opt.update.split(','), 1) or {}

        self.options['translate_modules'] = opt.translate_modules and map(lambda m: m.strip(), opt.translate_modules.split(',')) or ['all']
        self.options['translate_modules'].sort()

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
            import _winreg
            x=_winreg.ConnectRegistry(None,_winreg.HKEY_LOCAL_MACHINE)
            y = _winreg.OpenKey(x, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment", 0,_winreg.KEY_ALL_ACCESS)
            _winreg.SetValueEx(y,"PGPASSFILE", 0, _winreg.REG_EXPAND_SZ, filename )
            _winreg.CloseKey(y)
            _winreg.CloseKey(x)
        else:
            import stat
            os.chmod(filename, stat.S_IRUSR + stat.S_IWUSR)

    def _check_addons_path(self, option, opt, value, parser):
        res = os.path.abspath(os.path.expanduser(value))
        if not os.path.exists(res):
            raise optparse.OptionValueError("option %s: no such directory: %r" % (opt, value))

        contains_addons = False
        for f in os.listdir(res):
            modpath = os.path.join(res, f)
            if os.path.isdir(modpath) and os.path.exists(os.path.join(modpath, '__init__.py')) and \
            os.path.exists(os.path.join(modpath, '__terp__.py')):
                contains_addons = True
                break

        if not contains_addons:
            raise optparse.OptionValueError("option %s: The addons-path %r does not seem to a be a valid Addons Directory!" % (opt, value))

        
        setattr(parser.values, option.dest, res)

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
        except IOError:
            pass
        except ConfigParser.NoSectionError:
            pass

    def save(self):
        p = ConfigParser.ConfigParser()
        loglevelnames = dict(zip(self._LOGLEVELS.values(), self._LOGLEVELS.keys()))
        p.add_section('options')
        for opt in self.options.keys():
            if opt in ('version', 'language', 'translate_out', 'translate_in', 'init', 'update'):
                continue
            if opt in ('log_level', 'assert_exit_level'):
                p.set('options', opt, loglevelnames.get(self.options[opt], self.options[opt]))
            else:
                p.set('options', opt, self.options[opt])

        # try to create the directories and write the file
        try:
            if not os.path.exists(os.path.dirname(self.rcfile)):
                os.makedirs(os.path.dirname(self.rcfile))
            try:
                p.write(file(self.rcfile, 'w'))
                os.chmod(self.rcfile, 0600)
            except IOError:
                sys.stderr.write("ERROR: couldn't write the config file\n")

        except OSError:
            # what to do if impossible?
            sys.stderr.write("ERROR: couldn't create the config directory\n")

    def get(self, key, default=None):
        return self.options.get(key, default)

    def __setitem__(self, key, value):
        self.options[key] = value

    def __getitem__(self, key):
        return self.options[key]

config = configmanager()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

