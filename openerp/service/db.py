# -*- coding: utf-8 -*-
from contextlib import closing
from functools import wraps
import logging
import os
import shutil
import threading
import traceback
import tempfile
import zipfile

import psycopg2

import openerp
from openerp import SUPERUSER_ID
from openerp.exceptions import Warning
import openerp.release
import openerp.sql_db
import openerp.tools

import security

_logger = logging.getLogger(__name__)

self_actions = {}
self_id = 0
self_id_protect = threading.Semaphore()

class DatabaseExists(Warning):
    pass

# This should be moved to openerp.modules.db, along side initialize().
def _initialize_db(id, db_name, demo, lang, user_password):
    try:
        self_actions[id]['progress'] = 0
        db = openerp.sql_db.db_connect(db_name)
        with closing(db.cursor()) as cr:
            # TODO this should be removed as it is done by RegistryManager.new().
            openerp.modules.db.initialize(cr)
            openerp.tools.config['lang'] = lang
            cr.commit()

        registry = openerp.modules.registry.RegistryManager.new(
            db_name, demo, self_actions[id], update_module=True)

        with closing(db.cursor()) as cr:
            if lang:
                modobj = registry['ir.module.module']
                mids = modobj.search(cr, SUPERUSER_ID, [('state', '=', 'installed')])
                modobj.update_translations(cr, SUPERUSER_ID, mids, lang)

            # update admin's password and lang
            values = {'password': user_password, 'lang': lang}
            registry['res.users'].write(cr, SUPERUSER_ID, [SUPERUSER_ID], values)

            cr.execute('SELECT login, password FROM res_users ORDER BY login')
            self_actions[id].update(users=cr.dictfetchall(), clean=True)
            cr.commit()

    except Exception, e:
        self_actions[id].update(clean=False, exception=e)
        _logger.exception('CREATE DATABASE failed:')
        self_actions[id]['traceback'] = traceback.format_exc()

def dispatch(method, params):
    if method in ['create', 'get_progress', 'drop', 'dump', 'restore', 'rename',
                  'change_admin_password', 'migrate_databases',
                  'create_database', 'duplicate_database']:
        passwd = params[0]
        params = params[1:]
        security.check_super(passwd)
    elif method in ['db_exist', 'list', 'list_lang', 'server_version']:
        # params = params
        # No security check for these methods
        pass
    else:
        raise KeyError("Method not found: %s" % method)
    fn = globals()['exp_' + method]
    return fn(*params)

def _create_empty_database(name):
    db = openerp.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        chosen_template = openerp.tools.config['db_template']
        cr.execute("SELECT datname FROM pg_database WHERE datname = %s",
                   (name,))
        if cr.fetchall():
            raise DatabaseExists("database %r already exists!" % (name,))
        else:
            cr.autocommit(True)     # avoid transaction block
            cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """ % (name, chosen_template))

def exp_create(db_name, demo, lang, user_password='admin'):
    self_id_protect.acquire()
    global self_id
    self_id += 1
    id = self_id
    self_id_protect.release()

    self_actions[id] = {'clean': False}

    _create_empty_database(db_name)

    _logger.info('CREATE DATABASE %s', db_name.lower())
    create_thread = threading.Thread(target=_initialize_db,
                                     args=(id, db_name, demo, lang, user_password))
    create_thread.start()
    self_actions[id]['thread'] = create_thread
    return id

def exp_create_database(db_name, demo, lang, user_password='admin'):
    """ Similar to exp_create but blocking."""
    self_id_protect.acquire()
    global self_id
    self_id += 1
    id = self_id
    self_id_protect.release()

    self_actions[id] = {'clean': False}

    _logger.info('Create database `%s`.', db_name)
    _create_empty_database(db_name)
    _initialize_db(id, db_name, demo, lang, user_password)
    return True

def exp_duplicate_database(db_original_name, db_name):
    _logger.info('Duplicate database `%s` to `%s`.', db_original_name, db_name)
    openerp.sql_db.close_db(db_original_name)
    db = openerp.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """ % (db_name, db_original_name))

    from_fs = openerp.tools.config.filestore(db_original_name)
    to_fs = openerp.tools.config.filestore(db_name)
    if os.path.exists(from_fs) and not os.path.exists(to_fs):
        shutil.copytree(from_fs, to_fs)
    return True

def exp_get_progress(id):
    if self_actions[id]['thread'].isAlive():
#       return openerp.modules.init_progress[db_name]
        return min(self_actions[id].get('progress', 0), 0.95), []
    else:
        clean = self_actions[id]['clean']
        if clean:
            users = self_actions[id]['users']
            for user in users:
                # Remove the None passwords as they can't be marshalled by XML-RPC.
                if user['password'] is None:
                    user['password'] = ''
            self_actions.pop(id)
            return 1.0, users
        else:
            a = self_actions.pop(id)
            exc, tb = a['exception'], a['traceback']
            raise Exception, exc, tb


def _drop_conn(cr, db_name):
    # Try to terminate all other connections that might prevent
    # dropping the database
    try:
        # PostgreSQL 9.2 renamed pg_stat_activity.procpid to pid:
        # http://www.postgresql.org/docs/9.2/static/release-9-2.html#AEN110389
        pid_col = 'pid' if cr._cnx.server_version >= 90200 else 'procpid'

        cr.execute("""SELECT pg_terminate_backend(%(pid_col)s)
                      FROM pg_stat_activity
                      WHERE datname = %%s AND
                            %(pid_col)s != pg_backend_pid()""" % {'pid_col': pid_col},
                   (db_name,))
    except Exception:
        pass


def exp_drop(db_name):
    if db_name not in exp_list(True):
        return False
    openerp.modules.registry.RegistryManager.delete(db_name)
    openerp.sql_db.close_db(db_name)

    db = openerp.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        cr.autocommit(True) # avoid transaction block
        _drop_conn(cr, db_name)

        try:
            cr.execute('DROP DATABASE "%s"' % db_name)
        except Exception, e:
            _logger.error('DROP DB: %s failed:\n%s', db_name, e)
            raise Exception("Couldn't drop database %s: %s" % (db_name, e))
        else:
            _logger.info('DROP DB: %s', db_name)

    fs = openerp.tools.config.filestore(db_name)
    if os.path.exists(fs):
        shutil.rmtree(fs)
    return True

def _set_pg_password_in_environment(func):
    """ On systems where pg_restore/pg_dump require an explicit
    password (i.e. when not connecting via unix sockets, and most
    importantly on Windows), it is necessary to pass the PG user
    password in the environment or in a special .pgpass file.

    This decorator handles setting
    :envvar:`PGPASSWORD` if it is not already
    set, and removing it afterwards.

    See also http://www.postgresql.org/docs/8.4/static/libpq-envars.html

    .. note:: This is not thread-safe, and should never be enabled for
         SaaS (giving SaaS users the super-admin password is not a good idea
         anyway)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if os.environ.get('PGPASSWORD') or not openerp.tools.config['db_password']:
            return func(*args, **kwargs)
        else:
            os.environ['PGPASSWORD'] = openerp.tools.config['db_password']
            try:
                return func(*args, **kwargs)
            finally:
                del os.environ['PGPASSWORD']
    return wrapper

def exp_dump(db_name):
    with tempfile.TemporaryFile() as t:
        dump_db(db_name, t)
        t.seek(0)
        return t.read().encode('base64')

@_set_pg_password_in_environment
def dump_db(db, stream):
    """Dump database `db` into file-like object `stream`"""
    with openerp.tools.osutil.tempdir() as dump_dir:
        registry = openerp.modules.registry.RegistryManager.get(db)
        with registry.cursor() as cr:
            filestore = registry['ir.attachment']._filestore(cr, SUPERUSER_ID)
            if os.path.exists(filestore):
                shutil.copytree(filestore, os.path.join(dump_dir, 'filestore'))

        dump_file = os.path.join(dump_dir, 'dump.sql')
        cmd = ['pg_dump', '--format=p', '--no-owner', '--file=' + dump_file]
        if openerp.tools.config['db_user']:
            cmd.append('--username=' + openerp.tools.config['db_user'])
        if openerp.tools.config['db_host']:
            cmd.append('--host=' + openerp.tools.config['db_host'])
        if openerp.tools.config['db_port']:
            cmd.append('--port=' + str(openerp.tools.config['db_port']))
        cmd.append(db)

        if openerp.tools.exec_pg_command(*cmd):
            _logger.error('DUMP DB: %s failed! Please verify the configuration of the database '
                          'password on the server. You may need to create a .pgpass file for '
                          'authentication, or specify `db_password` in the server configuration '
                          'file.', db)
            raise Exception("Couldn't dump database")

        openerp.tools.osutil.zip_dir(dump_dir, stream, include_dir=False)

    _logger.info('DUMP DB successful: %s', db)

def exp_restore(db_name, data, copy=False):
    data_file = tempfile.NamedTemporaryFile(delete=False)
    try:
        data_file.write(data.decode('base64'))
        data_file.close()
        restore_db(db_name, data_file.name, copy=copy)
    finally:
        os.unlink(data_file.name)
    return True

@_set_pg_password_in_environment
def restore_db(db, dump_file, copy=False):
    assert isinstance(db, basestring)
    if exp_db_exist(db):
        _logger.warning('RESTORE DB: %s already exists', db)
        raise Exception("Database already exists")

    _create_empty_database(db)

    filestore_path = None
    with openerp.tools.osutil.tempdir() as dump_dir:
        if zipfile.is_zipfile(dump_file):
            # v8 format
            with zipfile.ZipFile(dump_file, 'r') as z:
                # only extract known members!
                filestore = [m for m in z.namelist() if m.startswith('filestore/')]
                z.extractall(dump_dir, ['dump.sql'] + filestore)

                if filestore:
                    filestore_path = os.path.join(dump_dir, 'filestore')

            pg_cmd = 'psql'
            pg_args = ['-q', '-f', os.path.join(dump_dir, 'dump.sql')]

        else:
            # <= 7.0 format (raw pg_dump output)
            pg_cmd = 'pg_restore'
            pg_args = ['--no-owner', dump_file]

        args = []
        if openerp.tools.config['db_user']:
            args.append('--username=' + openerp.tools.config['db_user'])
        if openerp.tools.config['db_host']:
            args.append('--host=' + openerp.tools.config['db_host'])
        if openerp.tools.config['db_port']:
            args.append('--port=' + str(openerp.tools.config['db_port']))
        args.append('--dbname=' + db)
        pg_args = args + pg_args

        if openerp.tools.exec_pg_command(pg_cmd, *pg_args):
            raise Exception("Couldn't restore database")

        registry = openerp.modules.registry.RegistryManager.new(db)
        with registry.cursor() as cr:
            if copy:
                # if it's a copy of a database, force generation of a new dbuuid
                registry['ir.config_parameter'].init(cr, force=True)
            if filestore_path:
                filestore_dest = registry['ir.attachment']._filestore(cr, SUPERUSER_ID)
                shutil.move(filestore_path, filestore_dest)

            if openerp.tools.config['unaccent']:
                try:
                    with cr.savepoint():
                        cr.execute("CREATE EXTENSION unaccent")
                except psycopg2.Error:
                    pass

    _logger.info('RESTORE DB: %s', db)

def exp_rename(old_name, new_name):
    openerp.modules.registry.RegistryManager.delete(old_name)
    openerp.sql_db.close_db(old_name)

    db = openerp.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        cr.autocommit(True)     # avoid transaction block
        _drop_conn(cr, old_name)
        try:
            cr.execute('ALTER DATABASE "%s" RENAME TO "%s"' % (old_name, new_name))
            _logger.info('RENAME DB: %s -> %s', old_name, new_name)
        except Exception, e:
            _logger.error('RENAME DB: %s -> %s failed:\n%s', old_name, new_name, e)
            raise Exception("Couldn't rename database %s to %s: %s" % (old_name, new_name, e))

    old_fs = openerp.tools.config.filestore(old_name)
    new_fs = openerp.tools.config.filestore(new_name)
    if os.path.exists(old_fs) and not os.path.exists(new_fs):
        shutil.move(old_fs, new_fs)
    return True

@openerp.tools.mute_logger('openerp.sql_db')
def exp_db_exist(db_name):
    ## Not True: in fact, check if connection to database is possible. The database may exists
    return bool(openerp.sql_db.db_connect(db_name))

def exp_list(document=False):
    if not openerp.tools.config['list_db'] and not document:
        raise openerp.exceptions.AccessDenied()
    chosen_template = openerp.tools.config['db_template']
    templates_list = tuple(set(['template0', 'template1', 'postgres', chosen_template]))
    db = openerp.sql_db.db_connect('postgres')
    with closing(db.cursor()) as cr:
        try:
            db_user = openerp.tools.config["db_user"]
            if not db_user and os.name == 'posix':
                import pwd
                db_user = pwd.getpwuid(os.getuid())[0]
            if not db_user:
                cr.execute("select usename from pg_user where usesysid=(select datdba from pg_database where datname=%s)", (openerp.tools.config["db_name"],))
                res = cr.fetchone()
                db_user = res and str(res[0])
            if db_user:
                cr.execute("select datname from pg_database where datdba=(select usesysid from pg_user where usename=%s) and datname not in %s order by datname", (db_user, templates_list))
            else:
                cr.execute("select datname from pg_database where datname not in %s order by datname", (templates_list,))
            res = [openerp.tools.ustr(name) for (name,) in cr.fetchall()]
        except Exception:
            res = []
    res.sort()
    return res

def exp_change_admin_password(new_password):
    openerp.tools.config['admin_passwd'] = new_password
    openerp.tools.config.save()
    return True

def exp_list_lang():
    return openerp.tools.scan_languages()

def exp_server_version():
    """ Return the version of the server
        Used by the client to verify the compatibility with its own version
    """
    return openerp.release.version

def exp_migrate_databases(databases):
    for db in databases:
        _logger.info('migrate database %s', db)
        openerp.tools.config['update']['base'] = True
        openerp.modules.registry.RegistryManager.new(db, force_demo=False, update_module=True)
    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
