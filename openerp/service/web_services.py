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
    report_spool()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
