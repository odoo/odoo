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
from __future__ import with_statement
import contextlib
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
import openerp.service.model
import openerp.sql_db as sql_db
import openerp.tools as tools
import openerp.modules
import openerp.exceptions
import openerp.osv.orm # TODO use openerp.exceptions
from openerp.service import http_server
from openerp import SUPERUSER_ID

#.apidoc title: Exported Service methods
#.apidoc module-mods: member-order: bysource

""" This python module defines the RPC methods available to remote clients.

    Each 'Export Service' is a group of 'methods', which in turn are RPC
    procedures to be called. Each method has its own arguments footprint.
"""

_logger = logging.getLogger(__name__)

RPC_VERSION_1 = {
        'server_version': release.version,
        'server_version_info': release.version_info,
        'server_serie': release.serie,
        'protocol_version': 1,
}

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
            raise openerp.osv.orm.except_orm('Migration Error', str(e))


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
                _logger.info('create a new backup directory to store the old modules: %s', backup_directory)
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
            raise openerp.osv.orm.except_orm('Migration Error', str(e))
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
                environment += '%s'% lsbinfo
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
        return bool(sql_db.db_connect('postgres'))

    def exp_get_os_time(self):
        return os.times()

    def exp_get_sqlcount(self):
        if not logging.getLogger('openerp.sql_db').isEnabledFor(logging.DEBUG):
            _logger.warning("Counters of SQL will not be reliable unless logger openerp.sql_db is set to level DEBUG or higer.")
        return sql_db.sql_counter


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
        openerp.modules.registry.RegistryManager.check_registry_signaling(db)
        fn = getattr(self, 'exp_' + method)
        res = fn(db, uid, *params)
        openerp.modules.registry.RegistryManager.signal_caches_change(db)
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

            _logger.exception('Exception: %s\n', exception)
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
                _logger.exception('Exception: %s\n', exception)
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
            raise openerp.osv.orm.except_orm(exc.message, exc.traceback)
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


def start_service():
    common()
    report_spool()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
