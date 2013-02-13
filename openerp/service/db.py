# -*- coding: utf-8 -*-

import contextlib
import logging
import threading
import traceback

from openerp import SUPERUSER_ID
import openerp.pooler
import openerp.sql_db
import openerp.tools

import security

_logger = logging.getLogger(__name__)

self_actions = {}
self_id = 0
self_id_protect = threading.Semaphore()

# This should be moved to openerp.modules.db, along side initialize().
def _initialize_db(id, db_name, demo, lang, user_password):
    cr = None
    try:
        self_actions[id]['progress'] = 0
        cr = openerp.sql_db.db_connect(db_name).cursor()
        openerp.modules.db.initialize(cr) # TODO this should be removed as it is done by pooler.restart_pool.
        openerp.tools.config['lang'] = lang
        cr.commit()
        cr.close()

        pool = openerp.pooler.restart_pool(db_name, demo, self_actions[id],
                                   update_module=True)[1]

        cr = openerp.sql_db.db_connect(db_name).cursor()

        if lang:
            modobj = pool.get('ir.module.module')
            mids = modobj.search(cr, SUPERUSER_ID, [('state', '=', 'installed')])
            modobj.update_translations(cr, SUPERUSER_ID, mids, lang)

        # update admin's password and lang
        values = {'password': user_password, 'lang': lang}
        pool.get('res.users').write(cr, SUPERUSER_ID, [SUPERUSER_ID], values)

        cr.execute('SELECT login, password FROM res_users ORDER BY login')
        self_actions[id].update(users=cr.dictfetchall(), clean=True)
        cr.commit()
        cr.close()
    except Exception, e:
        self_actions[id].update(clean=False, exception=e)
        _logger.exception('CREATE DATABASE failed:')
        self_actions[id]['traceback'] = traceback.format_exc()
        if cr:
            cr.close()

def dispatch(method, params):
    if method in [ 'create', 'get_progress', 'drop', 'dump',
        'restore', 'rename',
        'change_admin_password', 'migrate_databases',
        'create_database', 'duplicate_database' ]:
        passwd = params[0]
        params = params[1:]
        security.check_super(passwd)
    elif method in [ 'db_exist', 'list', 'list_lang', 'server_version' ]:
        # params = params
        # No security check for these methods
        pass
    else:
        raise KeyError("Method not found: %s" % method)
    fn = globals()['exp_' + method]
    return fn(*params)

def _create_empty_database(name):
    db = openerp.sql_db.db_connect('postgres')
    cr = db.cursor()
    chosen_template = openerp.tools.config['db_template']
    cr.execute("""SELECT datname 
                          FROM pg_database
                          WHERE datname = %s """,
                       (name,))
    if cr.fetchall():
        raise openerp.exceptions.Warning(" %s database already exists!" % name )
    try:
        cr.autocommit(True) # avoid transaction block
        cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """ % (name, chosen_template))
    finally:
        cr.close()

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
    cr = db.cursor()
    try:
        cr.autocommit(True) # avoid transaction block
        cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """ % (db_name, db_original_name))
    finally:
        cr.close()
    return True

def exp_get_progress(id):
    if self_actions[id]['thread'].isAlive():
#       return openerp.modules.init_progress[db_name]
        return min(self_actions[id].get('progress', 0),0.95), []
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
            e = self_actions[id]['exception'] # TODO this seems wrong: actions[id]['traceback'] is set, but not 'exception'.
            self_actions.pop(id)
            raise Exception, e

def exp_drop(db_name):
    if not exp_db_exist(db_name):
        return False
    openerp.modules.registry.RegistryManager.delete(db_name)
    openerp.sql_db.close_db(db_name)

    db = openerp.sql_db.db_connect('postgres')
    cr = db.cursor()
    cr.autocommit(True) # avoid transaction block
    try:
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

        try:
            cr.execute('DROP DATABASE "%s"' % db_name)
        except Exception, e:
            _logger.error('DROP DB: %s failed:\n%s', db_name, e)
            raise Exception("Couldn't drop database %s: %s" % (db_name, e))
        else:
            _logger.info('DROP DB: %s', db_name)
    finally:
        cr.close()
    return True

@contextlib.contextmanager
def _set_pg_password_in_environment():
    """ On Win32, pg_dump (and pg_restore) require that
    :envvar:`PGPASSWORD` be set

    This context management method handles setting
    :envvar:`PGPASSWORD` iif win32 and the envvar is not already
    set, and removing it afterwards.
    """
    if os.name != 'nt' or os.environ.get('PGPASSWORD'):
        yield
    else:
        os.environ['PGPASSWORD'] = openerp.tools.config['db_password']
        try:
            yield
        finally:
            del os.environ['PGPASSWORD']


def exp_dump(db_name):
    with _set_pg_password_in_environment():
        cmd = ['pg_dump', '--format=c', '--no-owner']
        if openerp.tools.config['db_user']:
            cmd.append('--username=' + openerp.tools.config['db_user'])
        if openerp.tools.config['db_host']:
            cmd.append('--host=' + openerp.tools.config['db_host'])
        if openerp.tools.config['db_port']:
            cmd.append('--port=' + str(openerp.tools.config['db_port']))
        cmd.append(db_name)

        stdin, stdout = openerp.tools.exec_pg_command_pipe(*tuple(cmd))
        stdin.close()
        data = stdout.read()
        res = stdout.close()

        if not data or res:
            _logger.error(
                    'DUMP DB: %s failed! Please verify the configuration of the database password on the server. '
                    'It should be provided as a -w <PASSWD> command-line option, or as `db_password` in the '
                    'server configuration file.\n %s', db_name, data)
            raise Exception, "Couldn't dump database"
        _logger.info('DUMP DB successful: %s', db_name)

        return base64.encodestring(data)

def exp_restore(db_name, data):
    with _set_pg_password_in_environment():
        if exp_db_exist(db_name):
            _logger.warning('RESTORE DB: %s already exists', db_name)
            raise Exception, "Database already exists"

        _create_empty_database(db_name)

        cmd = ['pg_restore', '--no-owner']
        if openerp.tools.config['db_user']:
            cmd.append('--username=' + openerp.tools.config['db_user'])
        if openerp.tools.config['db_host']:
            cmd.append('--host=' + openerp.tools.config['db_host'])
        if openerp.tools.config['db_port']:
            cmd.append('--port=' + str(openerp.tools.config['db_port']))
        cmd.append('--dbname=' + db_name)
        args2 = tuple(cmd)

        buf=base64.decodestring(data)
        if os.name == "nt":
            tmpfile = (os.environ['TMP'] or 'C:\\') + os.tmpnam()
            file(tmpfile, 'wb').write(buf)
            args2=list(args2)
            args2.append(tmpfile)
            args2=tuple(args2)
        stdin, stdout = openerp.tools.exec_pg_command_pipe(*args2)
        if not os.name == "nt":
            stdin.write(base64.decodestring(data))
        stdin.close()
        res = stdout.close()
        if res:
            raise Exception, "Couldn't restore database"
        _logger.info('RESTORE DB: %s', db_name)

        return True

def exp_rename(old_name, new_name):
    openerp.modules.registry.RegistryManager.delete(old_name)
    openerp.sql_db.close_db(old_name)

    db = openerp.sql_db.db_connect('postgres')
    cr = db.cursor()
    cr.autocommit(True) # avoid transaction block
    try:
        try:
            cr.execute('ALTER DATABASE "%s" RENAME TO "%s"' % (old_name, new_name))
        except Exception, e:
            _logger.error('RENAME DB: %s -> %s failed:\n%s', old_name, new_name, e)
            raise Exception("Couldn't rename database %s to %s: %s" % (old_name, new_name, e))
        else:
            fs = os.path.join(openerp.tools.config['root_path'], 'filestore')
            if os.path.exists(os.path.join(fs, old_name)):
                os.rename(os.path.join(fs, old_name), os.path.join(fs, new_name))

            _logger.info('RENAME DB: %s -> %s', old_name, new_name)
    finally:
        cr.close()
    return True

def exp_db_exist(db_name):
    ## Not True: in fact, check if connection to database is possible. The database may exists
    return bool(openerp.sql_db.db_connect(db_name))

def exp_list(document=False):
    if not openerp.tools.config['list_db'] and not document:
        raise openerp.exceptions.AccessDenied()
    chosen_template = openerp.tools.config['db_template']
    templates_list = tuple(set(['template0', 'template1', 'postgres', chosen_template]))
    db = openerp.sql_db.db_connect('postgres')
    cr = db.cursor()
    try:
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
            res = [str(name) for (name,) in cr.fetchall()]
        except Exception:
            res = []
    finally:
        cr.close()
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
    return release.version

def exp_migrate_databases(databases):
    for db in databases:
        _logger.info('migrate database %s', db)
        openerp.tools.config['update']['base'] = True
        openerp.pooler.restart_pool(db, force_demo=False, update_module=True)
    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
