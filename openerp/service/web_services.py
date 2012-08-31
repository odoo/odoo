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

import base64
import locale
import logging
import os
import platform
import security
import sys
import thread
import threading
import time
import traceback
from cStringIO import StringIO
from openerp.tools.translate import _
import openerp.netsvc as netsvc
import openerp.pooler as pooler
import openerp.release as release
import openerp.sql_db as sql_db
import openerp.tools as tools
import openerp.modules
import openerp.exceptions
from openerp.service import http_server
from openerp import SUPERUSER_ID

#.apidoc title: Exported Service methods
#.apidoc module-mods: member-order: bysource

""" This python module defines the RPC methods available to remote clients.

    Each 'Export Service' is a group of 'methods', which in turn are RPC
    procedures to be called. Each method has its own arguments footprint.
"""

_logger = logging.getLogger(__name__)

RPC_VERSION_1 = {'server_version': '6.1', 'protocol_version': 1}

# This should be moved to openerp.modules.db, along side initialize().
def _initialize_db(serv, id, db_name, demo, lang, user_password):
    cr = None
    try:
        serv.actions[id]['progress'] = 0
        cr = sql_db.db_connect(db_name).cursor()
        openerp.modules.db.initialize(cr) # TODO this should be removed as it is done by pooler.restart_pool.
        tools.config['lang'] = lang
        cr.commit()
        cr.close()

        pool = pooler.restart_pool(db_name, demo, serv.actions[id],
                                   update_module=True)[1]

        cr = sql_db.db_connect(db_name).cursor()

        if lang:
            modobj = pool.get('ir.module.module')
            mids = modobj.search(cr, SUPERUSER_ID, [('state', '=', 'installed')])
            modobj.update_translations(cr, SUPERUSER_ID, mids, lang)

        cr.execute('UPDATE res_users SET password=%s, lang=%s, active=True WHERE login=%s', (
            user_password, lang, 'admin'))
        cr.execute('SELECT login, password ' \
                   ' FROM res_users ' \
                   ' ORDER BY login')
        serv.actions[id].update(users=cr.dictfetchall(), clean=True)
        cr.commit()
        cr.close()
    except Exception, e:
        serv.actions[id].update(clean=False, exception=e)
        _logger.exception('CREATE DATABASE failed:')
        serv.actions[id]['traceback'] = traceback.format_exc()
        if cr:
            cr.close()

class db(netsvc.ExportService):
    def __init__(self, name="db"):
        netsvc.ExportService.__init__(self, name)
        self.actions = {}
        self.id = 0
        self.id_protect = threading.Semaphore()

        self._pg_psw_env_var_is_set = False # on win32, pg_dump need the PGPASSWORD env var

    def dispatch(self, method, params):
        if method in [ 'create', 'get_progress', 'drop', 'dump',
            'restore', 'rename',
            'change_admin_password', 'migrate_databases',
            'create_database' ]:
            passwd = params[0]
            params = params[1:]
            security.check_super(passwd)
        elif method in [ 'db_exist', 'list', 'list_lang', 'server_version' ]:
            # params = params
            # No security check for these methods
            pass
        else:
            raise KeyError("Method not found: %s" % method)
        fn = getattr(self, 'exp_'+method)
        return fn(*params)

    def _create_empty_database(self, name):
        db = sql_db.db_connect('template1')
        cr = db.cursor()
        chosen_template = tools.config['db_template']
        try:
            cr.autocommit(True) # avoid transaction block
            cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "%s" """ % (name, chosen_template))
        finally:
            cr.close()

    def exp_create(self, db_name, demo, lang, user_password='admin'):
        self.id_protect.acquire()
        self.id += 1
        id = self.id
        self.id_protect.release()

        self.actions[id] = {'clean': False}

        self._create_empty_database(db_name)

        _logger.info('CREATE DATABASE %s', db_name.lower())
        create_thread = threading.Thread(target=_initialize_db,
                args=(self, id, db_name, demo, lang, user_password))
        create_thread.start()
        self.actions[id]['thread'] = create_thread
        return id

    def exp_create_database(self, db_name, demo, lang, user_password='admin'):
        """ Similar to exp_create but blocking."""
        self.id_protect.acquire()
        self.id += 1
        id = self.id
        self.id_protect.release()

        self.actions[id] = {'clean': False}

        _logger.info('CREATE DATABASE %s', db_name.lower())
        self._create_empty_database(db_name)
        _initialize_db(self, id, db_name, demo, lang, user_password)
        return True

    def exp_get_progress(self, id):
        if self.actions[id]['thread'].isAlive():
#           return openerp.modules.init_progress[db_name]
            return (min(self.actions[id].get('progress', 0),0.95), [])
        else:
            clean = self.actions[id]['clean']
            if clean:
                users = self.actions[id]['users']
                self.actions.pop(id)
                return (1.0, users)
            else:
                e = self.actions[id]['exception'] # TODO this seems wrong: actions[id]['traceback'] is set, but not 'exception'.
                self.actions.pop(id)
                raise Exception, e

    def exp_drop(self, db_name):
        if not self.exp_db_exist(db_name):
            return False
        openerp.modules.registry.RegistryManager.delete(db_name)
        sql_db.close_db(db_name)

        db = sql_db.db_connect('template1')
        cr = db.cursor()
        cr.autocommit(True) # avoid transaction block
        try:
            # Try to terminate all other connections that might prevent
            # dropping the database
            try:
                cr.execute("""SELECT pg_terminate_backend(procpid)
                              FROM pg_stat_activity
                              WHERE datname = %s AND 
                                    procpid != pg_backend_pid()""",
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


    def _set_pg_psw_env_var(self):
        # see http://www.postgresql.org/docs/8.4/static/libpq-envars.html
        # FIXME: This is not thread-safe, and should never be enabled for
        # SaaS (giving SaaS users the super-admin password is not a good idea
        # anyway)
        if tools.config['db_password'] and not os.environ.get('PGPASSWORD', ''):
            os.environ['PGPASSWORD'] = tools.config['db_password']
            self._pg_psw_env_var_is_set = True

    def _unset_pg_psw_env_var(self):
        if self._pg_psw_env_var_is_set:
            os.environ['PGPASSWORD'] = ''

    def exp_dump(self, db_name):
        try:
            self._set_pg_psw_env_var()
            cmd = ['pg_dump', '--format=c', '--no-owner']
            if tools.config['db_user']:
                cmd.append('--username=' + tools.config['db_user'])
            if tools.config['db_host']:
                cmd.append('--host=' + tools.config['db_host'])
            if tools.config['db_port']:
                cmd.append('--port=' + str(tools.config['db_port']))
            cmd.append(db_name)
    
            stdin, stdout = tools.exec_pg_command_pipe(*tuple(cmd))
            stdin.close()
            data = stdout.read()
            res = stdout.close()
    
            if not data or res:
                _logger.error(
                        'DUMP DB: %s failed! Please verify the configuration of the database password on the server. '\
                        'It should be provided as a -w <PASSWD> command-line option, or as `db_password` in the '\
                        'server configuration file.\n %s'  % (db_name, data))
                raise Exception, "Couldn't dump database"
            _logger.info('DUMP DB successful: %s', db_name)
    
            return base64.encodestring(data)
        finally:
            self._unset_pg_psw_env_var()

    def exp_restore(self, db_name, data):
        try:
            self._set_pg_psw_env_var()

            if self.exp_db_exist(db_name):
                _logger.warning('RESTORE DB: %s already exists' % (db_name,))
                raise Exception, "Database already exists"

            self._create_empty_database(db_name)

            cmd = ['pg_restore', '--no-owner']
            if tools.config['db_user']:
                cmd.append('--username=' + tools.config['db_user'])
            if tools.config['db_host']:
                cmd.append('--host=' + tools.config['db_host'])
            if tools.config['db_port']:
                cmd.append('--port=' + str(tools.config['db_port']))
            cmd.append('--dbname=' + db_name)
            args2 = tuple(cmd)

            buf=base64.decodestring(data)
            if os.name == "nt":
                tmpfile = (os.environ['TMP'] or 'C:\\') + os.tmpnam()
                file(tmpfile, 'wb').write(buf)
                args2=list(args2)
                args2.append(tmpfile)
                args2=tuple(args2)
            stdin, stdout = tools.exec_pg_command_pipe(*args2)
            if not os.name == "nt":
                stdin.write(base64.decodestring(data))
            stdin.close()
            res = stdout.close()
            if res:
                raise Exception, "Couldn't restore database"
            _logger.info('RESTORE DB: %s' % (db_name))

            return True
        finally:
            self._unset_pg_psw_env_var()

    def exp_rename(self, old_name, new_name):
        openerp.modules.registry.RegistryManager.delete(old_name)
        sql_db.close_db(old_name)

        db = sql_db.db_connect('template1')
        cr = db.cursor()
        cr.autocommit(True) # avoid transaction block
        try:
            try:
                cr.execute('ALTER DATABASE "%s" RENAME TO "%s"' % (old_name, new_name))
            except Exception, e:
                _logger.error('RENAME DB: %s -> %s failed:\n%s', old_name, new_name, e)
                raise Exception("Couldn't rename database %s to %s: %s" % (old_name, new_name, e))
            else:
                fs = os.path.join(tools.config['root_path'], 'filestore')
                if os.path.exists(os.path.join(fs, old_name)):
                    os.rename(os.path.join(fs, old_name), os.path.join(fs, new_name))

                _logger.info('RENAME DB: %s -> %s', old_name, new_name)
        finally:
            cr.close()
        return True

    def exp_db_exist(self, db_name):
        ## Not True: in fact, check if connection to database is possible. The database may exists
        return bool(sql_db.db_connect(db_name))

    def exp_list(self, document=False):
        if not tools.config['list_db'] and not document:
            raise openerp.exceptions.AccessDenied()
        chosen_template = tools.config['db_template']
        templates_list = tuple(set(['template0', 'template1', 'postgres', chosen_template]))
        db = sql_db.db_connect('template1')
        cr = db.cursor()
        try:
            try:
                db_user = tools.config["db_user"]
                if not db_user and os.name == 'posix':
                    import pwd
                    db_user = pwd.getpwuid(os.getuid())[0]
                if not db_user:
                    cr.execute("select usename from pg_user where usesysid=(select datdba from pg_database where datname=%s)", (tools.config["db_name"],))
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

    def exp_change_admin_password(self, new_password):
        tools.config['admin_passwd'] = new_password
        tools.config.save()
        return True

    def exp_list_lang(self):
        return tools.scan_languages()

    def exp_server_version(self):
        """ Return the version of the server
            Used by the client to verify the compatibility with its own version
        """
        return release.version

    def exp_migrate_databases(self,databases):

        from openerp.osv.orm import except_orm
        from openerp.osv.osv import except_osv

        for db in databases:
            try:
                _logger.info('migrate database %s', db)
                tools.config['update']['base'] = True
                pooler.restart_pool(db, force_demo=False, update_module=True)
            except except_orm, inst:
                netsvc.abort_response(1, inst.name, 'warning', inst.value)
            except except_osv, inst:
                netsvc.abort_response(1, inst.name, 'warning', inst.value)
            except Exception:
                _logger.exception('Exception in migrate_databases:')
                raise
        return True

class common(netsvc.ExportService):

    def __init__(self,name="common"):
        netsvc.ExportService.__init__(self,name)

    def dispatch(self, method, params):
        if method in ['login', 'about', 'timezone_get', 'get_server_environment',
                      'login_message','get_stats', 'check_connectivity',
                      'list_http_services', 'version', 'authenticate']:
            pass
        elif method in ['get_available_updates', 'get_migration_scripts', 'set_loglevel', 'get_os_time', 'get_sqlcount']:
            passwd = params[0]
            params = params[1:]
            security.check_super(passwd)
        else:
            raise Exception("Method not found: %s" % method)

        fn = getattr(self, 'exp_'+method)
        return fn(*params)

    def exp_login(self, db, login, password):
        # TODO: legacy indirection through 'security', should use directly
        # the res.users model
        res = security.login(db, login, password)
        msg = res and 'successful login' or 'bad login or password'
        _logger.info("%s from '%s' using database '%s'", msg, login, db.lower())
        return res or False

    def exp_authenticate(self, db, login, password, user_agent_env):
        res_users = pooler.get_pool(db).get('res.users')
        return res_users.authenticate(db, login, password, user_agent_env)

    def exp_version(self):
        return RPC_VERSION_1

    def exp_about(self, extended=False):
        """Return information about the OpenERP Server.

        @param extended: if True then return version info
        @return string if extended is False else tuple
        """

        info = _('''

OpenERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY - OpenERP SA''')

        if extended:
            return info, release.version
        return info

    def exp_timezone_get(self, db, login, password):
        return tools.misc.get_server_timezone()

    def exp_get_available_updates(self, contract_id, contract_password):
        import openerp.tools.maintenance as tm
        try:
            rc = tm.remote_contract(contract_id, contract_password)
            if not rc.id:
                raise tm.RemoteContractException('This contract does not exist or is not active')

            return rc.get_available_updates(rc.id, openerp.modules.get_modules_with_version())

        except tm.RemoteContractException, e:
            netsvc.abort_response(1, 'Migration Error', 'warning', str(e))


    def exp_get_migration_scripts(self, contract_id, contract_password):
        import openerp.tools.maintenance as tm
        try:
            rc = tm.remote_contract(contract_id, contract_password)
            if not rc.id:
                raise tm.RemoteContractException('This contract does not exist or is not active')
            if rc.status != 'full':
                raise tm.RemoteContractException('Can not get updates for a partial contract')

            _logger.info('starting migration with contract %s', rc.name)

            zips = rc.retrieve_updates(rc.id, openerp.modules.get_modules_with_version())

            from shutil import rmtree, copytree, copy

            backup_directory = os.path.join(tools.config['root_path'], 'backup', time.strftime('%Y-%m-%d-%H-%M'))
            if zips and not os.path.isdir(backup_directory):
                _logger.info('create a new backup directory to \
                                store the old modules: %s', backup_directory)
                os.makedirs(backup_directory)

            for module in zips:
                _logger.info('upgrade module %s', module)
                mp = openerp.modules.get_module_path(module)
                if mp:
                    if os.path.isdir(mp):
                        copytree(mp, os.path.join(backup_directory, module))
                        if os.path.islink(mp):
                            os.unlink(mp)
                        else:
                            rmtree(mp)
                    else:
                        copy(mp + 'zip', backup_directory)
                        os.unlink(mp + '.zip')

                try:
                    try:
                        base64_decoded = base64.decodestring(zips[module])
                    except Exception:
                        _logger.error('unable to read the module %s', module)
                        raise

                    zip_contents = StringIO(base64_decoded)
                    zip_contents.seek(0)
                    try:
                        try:
                            tools.extract_zip_file(zip_contents, tools.config['addons_path'] )
                        except Exception:
                            _logger.error('unable to extract the module %s', module)
                            rmtree(module)
                            raise
                    finally:
                        zip_contents.close()
                except Exception:
                    _logger.error('restore the previous version of the module %s', module)
                    nmp = os.path.join(backup_directory, module)
                    if os.path.isdir(nmp):
                        copytree(nmp, tools.config['addons_path'])
                    else:
                        copy(nmp+'.zip', tools.config['addons_path'])
                    raise

            return True
        except tm.RemoteContractException, e:
            netsvc.abort_response(1, 'Migration Error', 'warning', str(e))
        except Exception, e:
            _logger.exception('Exception in get_migration_script:')
            raise

    def exp_get_server_environment(self):
        os_lang = '.'.join( [x for x in locale.getdefaultlocale() if x] )
        if not os_lang:
            os_lang = 'NOT SET'
        environment = '\nEnvironment Information : \n' \
                     'System : %s\n' \
                     'OS Name : %s\n' \
                     %(platform.platform(), platform.os.name)
        if os.name == 'posix':
          if platform.system() == 'Linux':
             lsbinfo = os.popen('lsb_release -a').read()
             environment += '%s'%(lsbinfo)
          else:
             environment += 'Your System is not lsb compliant\n'
        environment += 'Operating System Release : %s\n' \
                    'Operating System Version : %s\n' \
                    'Operating System Architecture : %s\n' \
                    'Operating System Locale : %s\n'\
                    'Python Version : %s\n'\
                    'OpenERP-Server Version : %s'\
                    %(platform.release(), platform.version(), platform.architecture()[0],
                      os_lang, platform.python_version(),release.version)
        return environment

    def exp_login_message(self):
        return tools.config.get('login_message', False)

    def exp_set_loglevel(self, loglevel, logger=None):
        # TODO Previously, the level was set on the now deprecated
        # `openerp.netsvc.Logger` class.
        return True

    def exp_get_stats(self):
        res = "OpenERP server: %d threads\n" % threading.active_count()
        res += netsvc.Server.allStats()
        return res

    def exp_list_http_services(self):
        return http_server.list_http_services()

    def exp_check_connectivity(self):
        return bool(sql_db.db_connect('template1'))

    def exp_get_os_time(self):
        return os.times()

    def exp_get_sqlcount(self):
        if not logging.getLogger('openerp.sql_db').isEnabledFor(logging.DEBUG):
            _logger.warning("Counters of SQL will not be reliable unless logger openerp.sql_db is set to level DEBUG or higer.")
        return sql_db.sql_counter


class objects_proxy(netsvc.ExportService):
    def __init__(self, name="object"):
        netsvc.ExportService.__init__(self,name)

    def dispatch(self, method, params):
        (db, uid, passwd ) = params[0:3]
        threading.current_thread().uid = uid
        params = params[3:]
        if method == 'obj_list':
            raise NameError("obj_list has been discontinued via RPC as of 6.0, please query ir.model directly!")
        if method not in ['execute', 'execute_kw', 'exec_workflow']:
            raise NameError("Method not available %s" % method)
        security.check(db,uid,passwd)
        assert openerp.osv.osv.service, "The object_proxy class must be started with start_object_proxy."
        fn = getattr(openerp.osv.osv.service, method)
        res = fn(db, uid, *params)
        return res


#
# Wizard ID: 1
#    - None = end of wizard
#
# Wizard Type: 'form'
#    - form
#    - print
#
# Wizard datas: {}
# TODO: change local request to OSE request/reply pattern
#
class wizard(netsvc.ExportService):
    def __init__(self, name='wizard'):
        netsvc.ExportService.__init__(self,name)
        self.id = 0
        self.wiz_datas = {}
        self.wiz_name = {}
        self.wiz_uid = {}

    def dispatch(self, method, params):
        (db, uid, passwd ) = params[0:3]
        threading.current_thread().uid = uid
        params = params[3:]
        if method not in ['execute','create']:
            raise KeyError("Method not supported %s" % method)
        security.check(db,uid,passwd)
        fn = getattr(self, 'exp_'+method)
        res = fn(db, uid, *params)
        return res

    def _execute(self, db, uid, wiz_id, datas, action, context):
        self.wiz_datas[wiz_id].update(datas)
        wiz = netsvc.LocalService('wizard.'+self.wiz_name[wiz_id])
        return wiz.execute(db, uid, self.wiz_datas[wiz_id], action, context)

    def exp_create(self, db, uid, wiz_name, datas=None):
        if not datas:
            datas={}
#FIXME: this is not thread-safe
        self.id += 1
        self.wiz_datas[self.id] = {}
        self.wiz_name[self.id] = wiz_name
        self.wiz_uid[self.id] = uid
        return self.id

    def exp_execute(self, db, uid, wiz_id, datas, action='init', context=None):
        if not context:
            context={}

        if wiz_id in self.wiz_uid:
            if self.wiz_uid[wiz_id] == uid:
                return self._execute(db, uid, wiz_id, datas, action, context)
            else:
                raise openerp.exceptions.AccessDenied()
        else:
            raise openerp.exceptions.Warning('Wizard not found.')

#
# TODO: set a maximum report number per user to avoid DOS attacks
#
# Report state:
#     False -> True
#

class report_spool(netsvc.ExportService):
    def __init__(self, name='report'):
        netsvc.ExportService.__init__(self, name)
        self._reports = {}
        self.id = 0
        self.id_protect = threading.Semaphore()

    def dispatch(self, method, params):
        (db, uid, passwd ) = params[0:3]
        threading.current_thread().uid = uid
        params = params[3:]
        if method not in ['report', 'report_get', 'render_report']:
            raise KeyError("Method not supported %s" % method)
        security.check(db,uid,passwd)
        fn = getattr(self, 'exp_' + method)
        res = fn(db, uid, *params)
        return res

    def exp_render_report(self, db, uid, object, ids, datas=None, context=None):
        if not datas:
            datas={}
        if not context:
            context={}

        self.id_protect.acquire()
        self.id += 1
        id = self.id
        self.id_protect.release()

        self._reports[id] = {'uid': uid, 'result': False, 'state': False, 'exception': None}

        cr = pooler.get_db(db).cursor()
        try:
            obj = netsvc.LocalService('report.'+object)
            (result, format) = obj.create(cr, uid, ids, datas, context)
            if not result:
                tb = sys.exc_info()
                self._reports[id]['exception'] = openerp.exceptions.DeferredException('RML is not available at specified location or not enough data to print!', tb)
            self._reports[id]['result'] = result
            self._reports[id]['format'] = format
            self._reports[id]['state'] = True
        except Exception, exception:

            _logger.exception('Exception: %s\n', str(exception))
            if hasattr(exception, 'name') and hasattr(exception, 'value'):
                self._reports[id]['exception'] = openerp.exceptions.DeferredException(tools.ustr(exception.name), tools.ustr(exception.value))
            else:
                tb = sys.exc_info()
                self._reports[id]['exception'] = openerp.exceptions.DeferredException(tools.exception_to_unicode(exception), tb)
            self._reports[id]['state'] = True
        cr.commit()
        cr.close()

        return self._check_report(id)

    def exp_report(self, db, uid, object, ids, datas=None, context=None):
        if not datas:
            datas={}
        if not context:
            context={}

        self.id_protect.acquire()
        self.id += 1
        id = self.id
        self.id_protect.release()

        self._reports[id] = {'uid': uid, 'result': False, 'state': False, 'exception': None}

        def go(id, uid, ids, datas, context):
            cr = pooler.get_db(db).cursor()
            try:
                obj = netsvc.LocalService('report.'+object)
                (result, format) = obj.create(cr, uid, ids, datas, context)
                if not result:
                    tb = sys.exc_info()
                    self._reports[id]['exception'] = openerp.exceptions.DeferredException('RML is not available at specified location or not enough data to print!', tb)
                self._reports[id]['result'] = result
                self._reports[id]['format'] = format
                self._reports[id]['state'] = True
            except Exception, exception:
                _logger.exception('Exception: %s\n', str(exception))
                if hasattr(exception, 'name') and hasattr(exception, 'value'):
                    self._reports[id]['exception'] = openerp.exceptions.DeferredException(tools.ustr(exception.name), tools.ustr(exception.value))
                else:
                    tb = sys.exc_info()
                    self._reports[id]['exception'] = openerp.exceptions.DeferredException(tools.exception_to_unicode(exception), tb)
                self._reports[id]['state'] = True
            cr.commit()
            cr.close()
            return True

        thread.start_new_thread(go, (id, uid, ids, datas, context))
        return id

    def _check_report(self, report_id):
        result = self._reports[report_id]
        exc = result['exception']
        if exc:
            netsvc.abort_response(exc, exc.message, 'warning', exc.traceback)
        res = {'state': result['state']}
        if res['state']:
            if tools.config['reportgz']:
                import zlib
                res2 = zlib.compress(result['result'])
                res['code'] = 'zlib'
            else:
                #CHECKME: why is this needed???
                if isinstance(result['result'], unicode):
                    res2 = result['result'].encode('latin1', 'replace')
                else:
                    res2 = result['result']
            if res2:
                res['result'] = base64.encodestring(res2)
            res['format'] = result['format']
            del self._reports[report_id]
        return res

    def exp_report_get(self, db, uid, report_id):
        if report_id in self._reports:
            if self._reports[report_id]['uid'] == uid:
                return self._check_report(report_id)
            else:
                raise Exception, 'AccessDenied'
        else:
            raise Exception, 'ReportNotFound'


def start_web_services():
    db()
    common()
    objects_proxy()
    wizard()
    report_spool()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

