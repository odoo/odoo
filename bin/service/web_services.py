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

import base64
import logging
import os
import security
import thread
import threading
import time
import sys
import platform
from tools.translate import _
import addons
import ir
import netsvc
import pooler
import release
import sql_db
import tools
import locale
from cStringIO import StringIO

logging.basicConfig()

class db(netsvc.Service):
    def __init__(self, name="db"):
        netsvc.Service.__init__(self, name)
        self.joinGroup("web-services")
        self.exportMethod(self.create)
        self.exportMethod(self.get_progress)
        self.exportMethod(self.drop)
        self.exportMethod(self.dump)
        self.exportMethod(self.restore)
        self.exportMethod(self.rename)
        self.exportMethod(self.list)
        self.exportMethod(self.list_lang)
        self.exportMethod(self.change_admin_password)
        self.exportMethod(self.server_version)
        self.exportMethod(self.migrate_databases)
        self.actions = {}
        self.id = 0
        self.id_protect = threading.Semaphore()

        self._pg_psw_env_var_is_set = False # on win32, pg_dump need the PGPASSWORD env var

    def _create_empty_database(self, name):
        db = sql_db.db_connect('template1')
        cr = db.cursor()
        try:
            cr.autocommit(True) # avoid transaction block
            cr.execute("""CREATE DATABASE "%s" ENCODING 'unicode' TEMPLATE "template0" """ % name)
        finally:
            cr.close()

    def create(self, password, db_name, demo, lang, user_password='admin'):
        security.check_super(password)
        self.id_protect.acquire()
        self.id += 1
        id = self.id
        self.id_protect.release()

        self.actions[id] = {'clean': False}

        self._create_empty_database(db_name)

        class DBInitialize(object):
            def __call__(self, serv, id, db_name, demo, lang, user_password='admin'):
                cr = None
                try:
                    serv.actions[id]['progress'] = 0
                    cr = sql_db.db_connect(db_name).cursor()
                    tools.init_db(cr)
                    cr.commit()
                    cr.close()
                    cr = None
                    pool = pooler.restart_pool(db_name, demo, serv.actions[id],
                            update_module=True)[1]

                    cr = sql_db.db_connect(db_name).cursor()

                    if lang:
                        modobj = pool.get('ir.module.module')
                        mids = modobj.search(cr, 1, [('state', '=', 'installed')])
                        modobj.update_translations(cr, 1, mids, lang)

                    cr.execute('UPDATE res_users SET password=%s, context_lang=%s, active=True WHERE login=%s', (
                        user_password, lang, 'admin'))
                    cr.execute('SELECT login, password, name ' \
                               '  FROM res_users ' \
                               ' ORDER BY login')
                    serv.actions[id]['users'] = cr.dictfetchall()
                    serv.actions[id]['clean'] = True
                    cr.commit()
                    cr.close()
                except Exception, e:
                    serv.actions[id]['clean'] = False
                    serv.actions[id]['exception'] = e
                    import traceback
                    e_str = StringIO()
                    traceback.print_exc(file=e_str)
                    traceback_str = e_str.getvalue()
                    e_str.close()
                    netsvc.Logger().notifyChannel('web-services', netsvc.LOG_ERROR, 'CREATE DATABASE\n%s' % (traceback_str))
                    serv.actions[id]['traceback'] = traceback_str
                    if cr:
                        cr.close()
        logger = netsvc.Logger()
        logger.notifyChannel("web-services", netsvc.LOG_INFO, 'CREATE DATABASE: %s' % (db_name.lower()))
        dbi = DBInitialize()
        create_thread = threading.Thread(target=dbi,
                args=(self, id, db_name, demo, lang, user_password))
        create_thread.start()
        self.actions[id]['thread'] = create_thread
        return id

    def get_progress(self, password, id):
        security.check_super(password)
        if self.actions[id]['thread'].isAlive():
#           return addons.init_progress[db_name]
            return (min(self.actions[id].get('progress', 0),0.95), [])
        else:
            clean = self.actions[id]['clean']
            if clean:
                users = self.actions[id]['users']
                self.actions.pop(id)
                return (1.0, users)
            else:
                e = self.actions[id]['exception']
                self.actions.pop(id)
                raise Exception, e

    def drop(self, password, db_name):
        security.check_super(password)
        sql_db.close_db(db_name)
        logger = netsvc.Logger()

        db = sql_db.db_connect('template1')
        cr = db.cursor()
        cr.autocommit(True) # avoid transaction block
        try:
            try:
                cr.execute('DROP DATABASE "%s"' % db_name)
            except Exception, e:
                logger.notifyChannel("web-services", netsvc.LOG_ERROR,
                        'DROP DB: %s failed:\n%s' % (db_name, e))
                raise Exception("Couldn't drop database %s: %s" % (db_name, e))
            else:
                logger.notifyChannel("web-services", netsvc.LOG_INFO,
                    'DROP DB: %s' % (db_name))
        finally:
            cr.close()
        return True

    def _set_pg_psw_env_var(self):
        if os.name == 'nt' and not os.environ.get('PGPASSWORD', ''):
            os.environ['PGPASSWORD'] = tools.config['db_password']
            self._pg_psw_env_var_is_set = True

    def _unset_pg_psw_env_var(self):
        if os.name == 'nt' and self._pg_psw_env_var_is_set:
            os.environ['PGPASSWORD'] = ''

    def dump(self, password, db_name):
        security.check_super(password)
        logger = netsvc.Logger()

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
        if res:
            logger.notifyChannel("web-services", netsvc.LOG_ERROR,
                    'DUMP DB: %s failed\n%s' % (db_name, data))
            raise Exception, "Couldn't dump database"
        logger.notifyChannel("web-services", netsvc.LOG_INFO,
                'DUMP DB: %s' % (db_name))

        self._unset_pg_psw_env_var()

        return base64.encodestring(data)

    def restore(self, password, db_name, data):
        security.check_super(password)
        logger = netsvc.Logger()

        self._set_pg_psw_env_var()

        if self.db_exist(db_name):
            logger.notifyChannel("web-services", netsvc.LOG_WARNING,
                    'RESTORE DB: %s already exists' % (db_name,))
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
            args2.append(' ' + tmpfile)
            args2=tuple(args2)
        stdin, stdout = tools.exec_pg_command_pipe(*args2)
        if not os.name == "nt":
            stdin.write(base64.decodestring(data))
        stdin.close()
        res = stdout.close()
        if res:
            raise Exception, "Couldn't restore database"
        logger.notifyChannel("web-services", netsvc.LOG_INFO,
                'RESTORE DB: %s' % (db_name))

        self._unset_pg_psw_env_var()

        return True

    def rename(self, password, old_name, new_name):
        security.check_super(password)
        sql_db.close_db(old_name)
        logger = netsvc.Logger()

        db = sql_db.db_connect('template1')
        cr = db.cursor()
        cr.autocommit(True) # avoid transaction block
        try:
            try:
                cr.execute('ALTER DATABASE "%s" RENAME TO "%s"' % (old_name, new_name))
            except Exception, e:
                logger.notifyChannel("web-services", netsvc.LOG_ERROR,
                        'RENAME DB: %s -> %s failed:\n%s' % (old_name, new_name, e))
                raise Exception("Couldn't rename database %s to %s: %s" % (old_name, new_name, e))
            else:
                fs = os.path.join(tools.config['root_path'], 'filestore')
                if os.path.exists(os.path.join(fs, old_name)):
                    os.rename(os.path.join(fs, old_name), os.path.join(fs, new_name))

                logger.notifyChannel("web-services", netsvc.LOG_INFO,
                    'RENAME DB: %s -> %s' % (old_name, new_name))
        finally:
            cr.close()
        return True

    def db_exist(self, db_name):
        ## Not True: in fact, check if connection to database is possible. The database may exists
        return bool(sql_db.db_connect(db_name))

    def list(self, document=False):
        if not tools.config['list_db'] and not document:
            raise Exception('AccessDenied')

        db = sql_db.db_connect('template1')
        cr = db.cursor()
        try:
            try:
                db_user = tools.config["db_user"]
                if not db_user and os.name == 'posix':
                    import pwd
                    db_user = pwd.getpwuid(os.getuid())[0]
                if not db_user:
                    cr.execute("select decode(usename, 'escape') from pg_user where usesysid=(select datdba from pg_database where datname=%s)", (tools.config["db_name"],))
                    res = cr.fetchone()
                    db_user = res and str(res[0])
                if db_user:
                    cr.execute("select decode(datname, 'escape') from pg_database where datdba=(select usesysid from pg_user where usename=%s) and datname not in ('template0', 'template1', 'postgres') order by datname", (db_user,))
                else:
                    cr.execute("select decode(datname, 'escape') from pg_database where datname not in('template0', 'template1','postgres') order by datname")
                res = [str(name) for (name,) in cr.fetchall()]
            except:
                res = []
        finally:
            cr.close()
        res.sort()
        return res

    def change_admin_password(self, old_password, new_password):
        security.check_super(old_password)
        tools.config['admin_passwd'] = new_password
        tools.config.save()
        return True

    def list_lang(self):
        return tools.scan_languages()

    def server_version(self):
        """ Return the version of the server
            Used by the client to verify the compatibility with its own version
        """
        return release.version

    def migrate_databases(self, password, databases):

        from osv.orm import except_orm
        from osv.osv import except_osv

        security.check_super(password)
        l = netsvc.Logger()
        for db in databases:
            try:
                l.notifyChannel('migration', netsvc.LOG_INFO, 'migrate database %s' % (db,))
                tools.config['update']['base'] = True
                pooler.restart_pool(db, force_demo=False, update_module=True)
            except except_orm, inst:
                self.abortResponse(1, inst.name, 'warning', inst.value)
            except except_osv, inst:
                self.abortResponse(1, inst.name, inst.exc_type, inst.value)
            except Exception:
                import traceback
                tb_s = reduce(lambda x, y: x+y, traceback.format_exception( sys.exc_type, sys.exc_value, sys.exc_traceback))
                l.notifyChannel('web-services', netsvc.LOG_ERROR, tb_s)
                raise
        return True
db()

class common(netsvc.Service):
    def __init__(self,name="common"):
        netsvc.Service.__init__(self,name)
        self.joinGroup("web-services")
        self.exportMethod(self.ir_get)
        self.exportMethod(self.ir_set)
        self.exportMethod(self.ir_del)
        self.exportMethod(self.about)
        self.exportMethod(self.login)
        self.exportMethod(self.logout)
        self.exportMethod(self.timezone_get)
        self.exportMethod(self.get_available_updates)
        self.exportMethod(self.get_migration_scripts)
        self.exportMethod(self.get_server_environment)
        self.exportMethod(self.login_message)
        self.exportMethod(self.check_connectivity)

    def ir_set(self, db, uid, password, keys, args, name, value, replace=True, isobject=False):
        security.check(db, uid, password)
        cr = pooler.get_db(db).cursor()
        res = ir.ir_set(cr,uid, keys, args, name, value, replace, isobject)
        cr.commit()
        cr.close()
        return res

    def ir_del(self, db, uid, password, id):
        security.check(db, uid, password)
        cr = pooler.get_db(db).cursor()
        res = ir.ir_del(cr,uid, id)
        cr.commit()
        cr.close()
        return res

    def ir_get(self, db, uid, password, keys, args=None, meta=None, context=None):
        if not args:
            args=[]
        if not context:
            context={}
        security.check(db, uid, password)
        cr = pooler.get_db(db).cursor()
        res = ir.ir_get(cr,uid, keys, args, meta, context)
        cr.commit()
        cr.close()
        return res

    def login(self, db, login, password):
        res = security.login(db, login, password)
        logger = netsvc.Logger()
        msg = res and 'successful login' or 'bad login or password'
        logger.notifyChannel("web-service", netsvc.LOG_INFO, "%s from '%s' using database '%s'" % (msg, login, db.lower()))
        return res or False

    def logout(self, db, login, password):
        logger = netsvc.Logger()
        logger.notifyChannel("web-service", netsvc.LOG_INFO,'Logout %s from database %s'%(login,db))
        return True

    def about(self, extended=False):
        """Return information about the OpenERP Server.

        @param extended: if True then return version info
        @return string if extended is False else tuple
        """

        info = _('''

OpenERP is an ERP+CRM program for small and medium businesses.

The whole source code is distributed under the terms of the
GNU Public Licence.

(c) 2003-TODAY, Fabien Pinckaers - Tiny sprl''')

        if extended:
            return info, release.version
        return info

    def timezone_get(self, db, login, password):
        return time.tzname[0]


    def get_available_updates(self, password, contract_id, contract_password):
        security.check_super(password)
        import tools.maintenance as tm
        try:
            rc = tm.remote_contract(contract_id, contract_password)
            if not rc.id:
                raise tm.RemoteContractException('This contract does not exist or is not active')

            return rc.get_available_updates(rc.id, addons.get_modules_with_version())

        except tm.RemoteContractException, e:
            self.abortResponse(1, 'Migration Error', 'warning', str(e))


    def get_migration_scripts(self, password, contract_id, contract_password):
        security.check_super(password)
        l = netsvc.Logger()
        import tools.maintenance as tm
        try:
            rc = tm.remote_contract(contract_id, contract_password)
            if not rc.id:
                raise tm.RemoteContractException('This contract does not exist or is not active')
            if rc.status != 'full':
                raise tm.RemoteContractException('Can not get updates for a partial contract')

            l.notifyChannel('migration', netsvc.LOG_INFO, 'starting migration with contract %s' % (rc.name,))

            zips = rc.retrieve_updates(rc.id, addons.get_modules_with_version())

            from shutil import rmtree, copytree, copy

            backup_directory = os.path.join(tools.config['root_path'], 'backup', time.strftime('%Y-%m-%d-%H-%M'))
            if zips and not os.path.isdir(backup_directory):
                l.notifyChannel('migration', netsvc.LOG_INFO, 'create a new backup directory to \
                                store the old modules: %s' % (backup_directory,))
                os.makedirs(backup_directory)

            for module in zips:
                l.notifyChannel('migration', netsvc.LOG_INFO, 'upgrade module %s' % (module,))
                mp = addons.get_module_path(module)
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
                    except:
                        l.notifyChannel('migration', netsvc.LOG_ERROR, 'unable to read the module %s' % (module,))
                        raise

                    zip_contents = StringIO(base64_decoded)
                    zip_contents.seek(0)
                    try:
                        try:
                            tools.extract_zip_file(zip_contents, tools.config['addons_path'] )
                        except:
                            l.notifyChannel('migration', netsvc.LOG_ERROR, 'unable to extract the module %s' % (module, ))
                            rmtree(module)
                            raise
                    finally:
                        zip_contents.close()
                except:
                    l.notifyChannel('migration', netsvc.LOG_ERROR, 'restore the previous version of the module %s' % (module, ))
                    nmp = os.path.join(backup_directory, module)
                    if os.path.isdir(nmp):
                        copytree(nmp, tools.config['addons_path'])
                    else:
                        copy(nmp+'.zip', tools.config['addons_path'])
                    raise

            return True
        except tm.RemoteContractException, e:
            self.abortResponse(1, 'Migration Error', 'warning', str(e))
        except Exception, e:
            import traceback
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception( sys.exc_type, sys.exc_value, sys.exc_traceback))
            l.notifyChannel('migration', netsvc.LOG_ERROR, tb_s)
            raise

    def get_server_environment(self):
        try:
            rev_id = os.popen('bzr revision-info').read()
        except Exception,e:
            rev_id = 'Exception: %s\n' % (tools.ustr(e))

        os_lang = '.'.join( [x for x in locale.getdefaultlocale() if x] )
        if not os_lang:
            os_lang = 'NOT SET'
        environment = '\nEnvironment Information : \n' \
                     'System : %s\n' \
                     'OS Name : %s\n' \
                     %(platform.platform(), platform.os.name)
        if os.name == 'posix':
          if platform.system() == 'Linux':
             lsbinfo = os.popen('lsb_release -idrc').read()
             environment += '%s'%(lsbinfo)
          else:
             environment += 'Your System is not lsb compliant\n'
        environment += 'Operating System Release : %s\n' \
                    'Operating System Version : %s\n' \
                    'Operating System Architecture : %s\n' \
                    'Operating System Locale : %s\n'\
                    'Python Version : %s\n'\
                    'OpenERP-Server Version : %s\n'\
                    'Last revision No. & ID : %s'\
                    %(platform.release(), platform.version(), platform.architecture()[0],
                      os_lang, platform.python_version(),release.version,rev_id)
        return environment

    def login_message(self):
        return tools.config.get('login_message', False)

    def check_connectivity(self):
        return bool(sql_db.db_connect('template1'))

common()

class objects_proxy(netsvc.Service):
    def __init__(self, name="object"):
        netsvc.Service.__init__(self,name)
        self.joinGroup('web-services')
        self.exportMethod(self.execute)
        self.exportMethod(self.exec_workflow)
        self.exportMethod(self.obj_list)

    def exec_workflow(self, db, uid, passwd, object, method, id):
        security.check(db, uid, passwd)
        service = netsvc.LocalService("object_proxy")
        res = service.exec_workflow(db, uid, object, method, id)
        return res

    def execute(self, db, uid, passwd, object, method, *args):
        security.check(db, uid, passwd)
        service = netsvc.LocalService("object_proxy")
        res = service.execute(db, uid, object, method, *args)
        return res

    def obj_list(self, db, uid, passwd):
        security.check(db, uid, passwd)
        service = netsvc.LocalService("object_proxy")
        res = service.obj_list()
        return res
objects_proxy()


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
class wizard(netsvc.Service):
    def __init__(self, name='wizard'):
        netsvc.Service.__init__(self,name)
        self.joinGroup('web-services')
        self.exportMethod(self.execute)
        self.exportMethod(self.create)
        self.id = 0
        self.wiz_datas = {}
        self.wiz_name = {}
        self.wiz_uid = {}

    def _execute(self, db, uid, wiz_id, datas, action, context):
        self.wiz_datas[wiz_id].update(datas)
        wiz = netsvc.LocalService('wizard.'+self.wiz_name[wiz_id])
        return wiz.execute(db, uid, self.wiz_datas[wiz_id], action, context)

    def create(self, db, uid, passwd, wiz_name, datas=None):
        if not datas:
            datas={}
        security.check(db, uid, passwd)
#FIXME: this is not thread-safe
        self.id += 1
        self.wiz_datas[self.id] = {}
        self.wiz_name[self.id] = wiz_name
        self.wiz_uid[self.id] = uid
        return self.id

    def execute(self, db, uid, passwd, wiz_id, datas, action='init', context=None):
        if not context:
            context={}
        security.check(db, uid, passwd)

        if wiz_id in self.wiz_uid:
            if self.wiz_uid[wiz_id] == uid:
                return self._execute(db, uid, wiz_id, datas, action, context)
            else:
                raise Exception, 'AccessDenied'
        else:
            raise Exception, 'WizardNotFound'
wizard()

#
# TODO: set a maximum report number per user to avoid DOS attacks
#
# Report state:
#     False -> True
#

class ExceptionWithTraceback(Exception):
    def __init__(self, msg, tb):
        self.message = msg
        self.traceback = tb
        self.args = (msg, tb)

class report_spool(netsvc.Service):
    def __init__(self, name='report'):
        netsvc.Service.__init__(self, name)
        self.joinGroup('web-services')
        self.exportMethod(self.report)
        self.exportMethod(self.report_get)
        self._reports = {}
        self.id = 0
        self.id_protect = threading.Semaphore()

    def report(self, db, uid, passwd, object, ids, datas=None, context=None):
        if not datas:
            datas={}
        if not context:
            context={}
        security.check(db, uid, passwd)

        self.id_protect.acquire()
        self.id += 1
        id = self.id
        self.id_protect.release()

        self._reports[id] = {'uid': uid, 'result': False, 'state': False, 'exception': None}

        def go(id, uid, ids, datas, context):
            cr = pooler.get_db(db).cursor()
            import traceback
            import sys
            try:
                obj = netsvc.LocalService('report.'+object)
                (result, format) = obj.create(cr, uid, ids, datas, context)
                if not result:
                    tb = sys.exc_info()
                    self._reports[id]['exception'] = ExceptionWithTraceback('RML is not available at specified location or not enough data to print!', tb)
                self._reports[id]['result'] = result
                self._reports[id]['format'] = format
                self._reports[id]['state'] = True
            except Exception, exception:
                
                tb = sys.exc_info()
                tb_s = "".join(traceback.format_exception(*tb))
                logger = netsvc.Logger()
                logger.notifyChannel('web-services', netsvc.LOG_ERROR,
                        'Exception: %s\n%s' % (str(exception), tb_s))
                self._reports[id]['exception'] = ExceptionWithTraceback(tools.exception_to_unicode(exception), tb)
                self._reports[id]['state'] = True
            cr.commit()
            cr.close()
            return True

        thread.start_new_thread(go, (id, uid, ids, datas, context))
        return id

    def _check_report(self, report_id):
        result = self._reports[report_id]
        if result['exception']:
            raise result['exception']
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

    def report_get(self, db, uid, passwd, report_id):
        security.check(db, uid, passwd)

        if report_id in self._reports:
            if self._reports[report_id]['uid'] == uid:
                return self._check_report(report_id)
            else:
                raise Exception, 'AccessDenied'
        else:
            raise Exception, 'ReportNotFound'

report_spool()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

