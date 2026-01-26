"""
slapdtest - module for spawning test instances of OpenLDAP's slapd server

See https://www.python-ldap.org/ for details.
"""
import os
import socket
import sys
import time
import subprocess
import logging
import atexit
from logging.handlers import SysLogHandler
import unittest
from shutil import which
from urllib.parse import quote_plus

# Switch off processing .ldaprc or ldap.conf before importing _ldap
os.environ['LDAPNOINIT'] = '1'

import ldap

HERE = os.path.abspath(os.path.dirname(__file__))

# a template string for generating simple slapd.d file
SLAPD_CONF_TEMPLATE = r"""dn: cn=config
objectClass: olcGlobal
cn: config
olcServerID: %(serverid)s
olcLogLevel: %(loglevel)s
olcAllows: bind_v2
olcAuthzRegexp: {0}"gidnumber=%(root_gid)s\+uidnumber=%(root_uid)s,cn=peercred,cn=external,cn=auth" "%(rootdn)s"
olcAuthzRegexp: {1}"C=DE, O=python-ldap, OU=slapd-test, CN=([A-Za-z]+)" "ldap://ou=people,dc=local???($1)"
olcTLSCACertificateFile: %(cafile)s
olcTLSCertificateFile: %(servercert)s
olcTLSCertificateKeyFile: %(serverkey)s
olcTLSVerifyClient: try

dn: cn=module,cn=config
objectClass: olcModuleList
cn: module
olcModuleLoad: back_%(database)s

dn: olcDatabase=%(database)s,cn=config
objectClass: olcDatabaseConfig
objectClass: olcMdbConfig
olcDatabase: %(database)s
olcSuffix: %(suffix)s
olcRootDN: %(rootdn)s
olcRootPW: %(rootpw)s
olcDbDirectory: %(directory)s
"""

LOCALHOST = '127.0.0.1'

CI_DISABLED = set(os.environ.get('CI_DISABLED', '').split(':'))
if 'LDAPI' in CI_DISABLED:
    HAVE_LDAPI = False
else:
    HAVE_LDAPI = hasattr(socket, 'AF_UNIX')


def identity(test_item):
    """Identity decorator

    """
    return test_item


def skip_unless_ci(reason, feature=None):
    """Skip test unless test case is executed on CI like Travis CI
    """
    if not os.environ.get('CI', False):
        return unittest.skip(reason)
    elif feature in CI_DISABLED:
        return unittest.skip(reason)
    else:
        # Don't skip on Travis
        return identity


def requires_tls():
    """Decorator for TLS tests

    Tests are not skipped on CI (e.g. Travis CI)
    """
    if not ldap.TLS_AVAIL:
        return skip_unless_ci("test needs ldap.TLS_AVAIL", feature='TLS')
    else:
        return identity


def requires_sasl():
    if not ldap.SASL_AVAIL:
        return skip_unless_ci(
            "test needs ldap.SASL_AVAIL", feature='SASL')
    else:
        return identity


def requires_ldapi():
    if not HAVE_LDAPI:
        return skip_unless_ci(
            "test needs ldapi support (AF_UNIX)", feature='LDAPI')
    else:
        return identity

def requires_init_fd():
    if not ldap.INIT_FD_AVAIL:
        return skip_unless_ci(
            "test needs ldap.INIT_FD", feature='INIT_FD')
    else:
        return identity


def _add_sbin(path):
    """Add /sbin and related directories to a command search path"""
    directories = path.split(os.pathsep)
    if sys.platform != 'win32':
        for sbin in '/usr/local/sbin', '/sbin', '/usr/sbin':
            if sbin not in directories:
                directories.append(sbin)
    return os.pathsep.join(directories)

def combined_logger(
        log_name,
        log_level=logging.WARN,
        sys_log_format='%(levelname)s %(message)s',
        console_log_format='%(asctime)s %(levelname)s %(message)s',
    ):
    """
    Returns a combined SysLogHandler/StreamHandler logging instance
    with formatters
    """
    if 'LOGLEVEL' in os.environ:
        log_level = os.environ['LOGLEVEL']
        try:
            log_level = int(log_level)
        except ValueError:
            pass
    # for writing to syslog
    new_logger = logging.getLogger(log_name)
    if sys_log_format and os.path.exists('/dev/log'):
        my_syslog_formatter = logging.Formatter(
            fmt=' '.join((log_name, sys_log_format)))
        my_syslog_handler = logging.handlers.SysLogHandler(
            address='/dev/log',
            facility=SysLogHandler.LOG_DAEMON,
        )
        my_syslog_handler.setFormatter(my_syslog_formatter)
        new_logger.addHandler(my_syslog_handler)
    if console_log_format:
        my_stream_formatter = logging.Formatter(fmt=console_log_format)
        my_stream_handler = logging.StreamHandler()
        my_stream_handler.setFormatter(my_stream_formatter)
        new_logger.addHandler(my_stream_handler)
    new_logger.setLevel(log_level)
    return new_logger  # end of combined_logger()


class SlapdObject:
    """
    Controller class for a slapd instance, OpenLDAP's server.

    This class creates a temporary data store for slapd, runs it
    listening on a private Unix domain socket and TCP port,
    and initializes it with a top-level entry and the root user.

    When a reference to an instance of this class is lost, the slapd
    server is shut down.

    An instance can be used as a context manager. When exiting the context
    manager, the slapd server is shut down and the temporary data store is
    removed.

    :param openldap_schema_files: A list of schema names or schema paths to
        load at startup. By default this only contains `core`.

    .. versionchanged:: 3.1

        Added context manager functionality
    """
    slapd_conf_template = SLAPD_CONF_TEMPLATE
    database = 'mdb'
    suffix = 'dc=slapd-test,dc=python-ldap,dc=org'
    root_cn = 'Manager'
    root_pw = 'password'
    slapd_loglevel = 'stats stats2'
    local_host = LOCALHOST
    testrunsubdirs = (
        'slapd.d',
    )
    openldap_schema_files = (
        'core.ldif',
    )

    TMPDIR = os.environ.get('TMP', os.getcwd())
    if 'SCHEMA' in os.environ:
        SCHEMADIR = os.environ['SCHEMA']
    elif os.path.isdir("/etc/openldap/schema"):
        SCHEMADIR = "/etc/openldap/schema"
    elif os.path.isdir("/etc/ldap/schema"):
        SCHEMADIR = "/etc/ldap/schema"
    else:
        SCHEMADIR = None

    BIN_PATH = os.environ.get('BIN', os.environ.get('PATH', os.defpath))
    SBIN_PATH = os.environ.get('SBIN', _add_sbin(BIN_PATH))

    # create loggers once, multiple calls mess up refleak tests
    _log = combined_logger('python-ldap-test')

    def __init__(self):
        self._proc = None
        self._port = self._avail_tcp_port()
        self.server_id = self._port % 4096
        self.testrundir = os.path.join(self.TMPDIR, 'python-ldap-test-%d' % self._port)
        self._slapd_conf = os.path.join(self.testrundir, 'slapd.d')
        self._db_directory = os.path.join(self.testrundir, "openldap-data")
        self.ldap_uri = "ldap://%s:%d/" % (self.local_host, self._port)
        if HAVE_LDAPI:
            ldapi_path = os.path.join(self.testrundir, 'ldapi')
            self.ldapi_uri = "ldapi://%s" % quote_plus(ldapi_path)
            self.default_ldap_uri = self.ldapi_uri
            # use SASL/EXTERNAL via LDAPI when invoking OpenLDAP CLI tools
            self.cli_sasl_external = ldap.SASL_AVAIL
        else:
            self.ldapi_uri = None
            self.default_ldap_uri = self.ldap_uri
            # Use simple bind via LDAP uri
            self.cli_sasl_external = False

        self._find_commands()

        if self.SCHEMADIR is None:
            raise ValueError('SCHEMADIR is None, ldap schemas are missing.')

        # TLS certs
        self.cafile = os.path.join(HERE, 'certs/ca.pem')
        self.servercert = os.path.join(HERE, 'certs/server.pem')
        self.serverkey = os.path.join(HERE, 'certs/server.key')
        self.clientcert = os.path.join(HERE, 'certs/client.pem')
        self.clientkey = os.path.join(HERE, 'certs/client.key')

    @property
    def root_dn(self):
        return 'cn={self.root_cn},{self.suffix}'.format(self=self)

    @property
    def hostname(self):
        return self.local_host

    @property
    def port(self):
        return self._port

    def _find_commands(self):
        self.PATH_LDAPADD = self._find_command('ldapadd')
        self.PATH_LDAPDELETE = self._find_command('ldapdelete')
        self.PATH_LDAPMODIFY = self._find_command('ldapmodify')
        self.PATH_LDAPWHOAMI = self._find_command('ldapwhoami')
        self.PATH_SLAPADD = self._find_command('slapadd')

        self.PATH_SLAPD = os.environ.get('SLAPD', None)
        if not self.PATH_SLAPD:
            self.PATH_SLAPD = self._find_command('slapd', in_sbin=True)

    def _find_command(self, cmd, in_sbin=False):
        if in_sbin:
            path = self.SBIN_PATH
            var_name = 'SBIN'
        else:
            path = self.BIN_PATH
            var_name = 'BIN'
        command = which(cmd, path=path)
        if command is None:
            raise ValueError(
                "Command '{}' not found. Set the {} environment variable to "
                "override slapdtest's search path.".format(cmd, var_name)
            )
        return command

    def setup_rundir(self):
        """
        creates rundir structure

        for setting up a custom directory structure you have to override
        this method
        """
        os.mkdir(self.testrundir)
        os.mkdir(self._db_directory)
        self._create_sub_dirs(self.testrunsubdirs)

    def _cleanup_rundir(self):
        """
        Recursively delete whole directory specified by `path'
        """
        # cleanup_rundir() is called in atexit handler. Until Python 3.4,
        # the rest of the world is already destroyed.
        import os, os.path
        if not os.path.exists(self.testrundir):
            return
        self._log.debug('clean-up %s', self.testrundir)
        for dirpath, dirnames, filenames in os.walk(
                self.testrundir,
                topdown=False
            ):
            for filename in filenames:
                self._log.debug('remove %s', os.path.join(dirpath, filename))
                os.remove(os.path.join(dirpath, filename))
            for dirname in dirnames:
                self._log.debug('rmdir %s', os.path.join(dirpath, dirname))
                os.rmdir(os.path.join(dirpath, dirname))
        os.rmdir(self.testrundir)
        self._log.info('cleaned-up %s', self.testrundir)

    def _avail_tcp_port(self):
        """
        find an available port for TCP connection
        """
        sock = socket.socket()
        try:
            sock.bind((self.local_host, 0))
            port = sock.getsockname()[1]
        finally:
            sock.close()
        self._log.info('Found available port %d', port)
        return port

    def gen_config(self):
        """
        generates a slapd.conf and returns it as one string

        for generating specific static configuration files you have to
        override this method
        """
        config_dict = {
            'serverid': hex(self.server_id),
            'loglevel': self.slapd_loglevel,
            'database': self.database,
            'directory': self._db_directory,
            'suffix': self.suffix,
            'rootdn': self.root_dn,
            'rootpw': self.root_pw,
            'root_uid': os.getuid(),
            'root_gid': os.getgid(),
            'cafile': self.cafile,
            'servercert': self.servercert,
            'serverkey': self.serverkey,
        }
        return self.slapd_conf_template % config_dict

    def _create_sub_dirs(self, dir_names):
        """
        create sub-directories beneath self.testrundir
        """
        for dname in dir_names:
            dir_name = os.path.join(self.testrundir, dname)
            self._log.debug('Create directory %s', dir_name)
            os.mkdir(dir_name)

    def _write_config(self):
        """Loads the slapd.d configuration."""
        self._log.debug("importing configuration: %s", self._slapd_conf)

        self.slapadd(self.gen_config(), ["-n0"])
        ldif_paths = [
            schema
            if os.path.exists(schema)
            else os.path.join(self.SCHEMADIR, schema)
            for schema in self.openldap_schema_files
        ]
        for ldif_path in ldif_paths:
            self.slapadd(None, ["-n0", "-l", ldif_path])

        self._log.debug("import ok: %s", self._slapd_conf)

    def _test_config(self):
        self._log.debug('testing config %s', self._slapd_conf)
        popen_list = [
            self.PATH_SLAPD,
            "-Ttest",
            "-F", self._slapd_conf,
            "-u",
            "-v",
            "-d", "config"
        ]
        p = subprocess.run(
            popen_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        if p.returncode != 0:
            self._log.error(p.stdout.decode("utf-8"))
            raise RuntimeError("configuration test failed")
        self._log.info("config ok: %s", self._slapd_conf)

    def _start_slapd(self):
        """
        Spawns/forks the slapd process
        """
        urls = [self.ldap_uri]
        if self.ldapi_uri:
            urls.append(self.ldapi_uri)
        slapd_args = [
            self.PATH_SLAPD,
            '-F', self._slapd_conf,
            '-h', ' '.join(urls),
        ]
        if self._log.isEnabledFor(logging.DEBUG):
            slapd_args.extend(['-d', '-1'])
        else:
            slapd_args.extend(['-d', '0'])
        self._log.info('starting slapd: %r', ' '.join(slapd_args))
        self._proc = subprocess.Popen(slapd_args)
        # Waits until the LDAP server socket is open, or slapd crashed
        deadline = time.monotonic() + 10
        # no cover to avoid spurious coverage changes, see
        # https://github.com/python-ldap/python-ldap/issues/127
        while True:  # pragma: no cover
            if self._proc.poll() is not None:
                self._stopped()
                raise RuntimeError("slapd exited before opening port")
            try:
                self._log.debug(
                    "slapd connection check to %s", self.default_ldap_uri
                )
                self.ldapwhoami()
            except RuntimeError:
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.2)
            else:
                return
        raise RuntimeError("slapd did not start properly")

    def start(self):
        """
        Starts the slapd server process running, and waits for it to come up.
        """

        if self._proc is None:
            # prepare directory structure
            atexit.register(self.stop)
            self._cleanup_rundir()
            self.setup_rundir()
            self._write_config()
            self._test_config()
            self._start_slapd()
            self._log.debug(
                'slapd with pid=%d listening on %s and %s',
                self._proc.pid, self.ldap_uri, self.ldapi_uri
            )

    def stop(self):
        """
        Stops the slapd server, and waits for it to terminate and cleans up
        """
        if self._proc is not None:
            self._log.debug('stopping slapd with pid %d', self._proc.pid)
            self._proc.terminate()
            self.wait()
        self._cleanup_rundir()
        atexit.unregister(self.stop)

    def restart(self):
        """
        Restarts the slapd server with same data
        """
        self._proc.terminate()
        self.wait()
        self._start_slapd()

    def wait(self):
        """Waits for the slapd process to terminate by itself."""
        if self._proc:
            self._proc.wait()
            self._stopped()

    def _stopped(self):
        """Called when the slapd server is known to have terminated"""
        if self._proc is not None:
            self._log.info('slapd[%d] terminated', self._proc.pid)
            self._proc = None

    def _cli_auth_args(self):
        if self.cli_sasl_external:
            authc_args = [
                '-Y', 'EXTERNAL',
            ]
            if not self._log.isEnabledFor(logging.DEBUG):
                authc_args.append('-Q')
        else:
            authc_args = [
                '-x',
                '-D', self.root_dn,
                '-w', self.root_pw,
            ]
        return authc_args

    # no cover to avoid spurious coverage changes
    def _cli_popen(self, ldapcommand, extra_args=None, ldap_uri=None,
                   stdin_data=None):  # pragma: no cover
        if ldap_uri is None:
            ldap_uri = self.default_ldap_uri

        if ldapcommand.split("/")[-1].startswith("ldap"):
            args = [ldapcommand, '-H', ldap_uri] + self._cli_auth_args()
        else:
            args = [ldapcommand, '-F', self._slapd_conf]

        args += (extra_args or [])

        self._log.debug('Run command: %r', ' '.join(args))
        proc = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self._log.debug('stdin_data=%r', stdin_data)
        stdout_data, stderr_data = proc.communicate(stdin_data)
        if stdout_data is not None:
            self._log.debug('stdout_data=%r', stdout_data)
        if stderr_data is not None:
            self._log.debug('stderr_data=%r', stderr_data)
        if proc.wait() != 0:
            raise RuntimeError(
                '{!r} process failed:\n{!r}\n{!r}'.format(
                    args, stdout_data, stderr_data
                )
            )
        return stdout_data, stderr_data

    def ldapwhoami(self, extra_args=None):
        """
        Runs ldapwhoami on this slapd instance
        """
        self._cli_popen(self.PATH_LDAPWHOAMI, extra_args=extra_args)

    def ldapadd(self, ldif, extra_args=None):
        """
        Runs ldapadd on this slapd instance, passing it the ldif content
        """
        self._cli_popen(self.PATH_LDAPADD, extra_args=extra_args,
                        stdin_data=ldif.encode('utf-8'))

    def ldapmodify(self, ldif, extra_args=None):
        """
        Runs ldapadd on this slapd instance, passing it the ldif content
        """
        self._cli_popen(self.PATH_LDAPMODIFY, extra_args=extra_args,
                        stdin_data=ldif.encode('utf-8'))

    def ldapdelete(self, dn, recursive=False, extra_args=None):
        """
        Runs ldapdelete on this slapd instance, deleting 'dn'
        """
        if extra_args is None:
            extra_args = []
        if recursive:
            extra_args.append('-r')
        extra_args.append(dn)
        self._cli_popen(self.PATH_LDAPDELETE, extra_args=extra_args)

    def slapadd(self, ldif, extra_args=None):
        """
        Runs slapadd on this slapd instance, passing it the ldif content
        """
        self._cli_popen(
            self.PATH_SLAPADD,
            stdin_data=ldif.encode("utf-8") if ldif else None,
            extra_args=extra_args,
        )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class SlapdTestCase(unittest.TestCase):
    """
    test class which also clones or initializes a running slapd
    """

    server_class = SlapdObject
    server = None
    ldap_object_class = None

    def _open_ldap_conn(self, who=None, cred=None, **kwargs):
        """
        return a LDAPObject instance after simple bind
        """
        ldap_conn = self.ldap_object_class(self.server.ldap_uri, **kwargs)
        ldap_conn.protocol_version = 3
        #ldap_conn.set_option(ldap.OPT_REFERRALS, 0)
        ldap_conn.simple_bind_s(who or self.server.root_dn, cred or self.server.root_pw)
        return ldap_conn

    @classmethod
    def setUpClass(cls):
        cls.server = cls.server_class()
        cls.server.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.stop()
