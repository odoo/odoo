# -*- coding: utf-8 -*-

import base64
import logging
import sys
import threading

import openerp
import openerp.report
from openerp import tools
from openerp.exceptions import UserError

import security

_logger = logging.getLogger(__name__)

# TODO: set a maximum report number per user to avoid DOS attacks
#
# Report state:
#     False -> True

self_reports = {}
self_id = 0
self_id_protect = threading.Semaphore()

def dispatch(method, params):
    (db, uid, passwd ) = params[0:3]
    threading.current_thread().uid = uid
    params = params[3:]
    if method not in ['report', 'report_get', 'render_report']:
        raise KeyError("Method not supported %s" % method)
    security.check(db,uid,passwd)
    openerp.modules.registry.RegistryManager.check_registry_signaling(db)
    fn = globals()['exp_' + method]
    res = fn(db, uid, *params)
    openerp.modules.registry.RegistryManager.signal_caches_change(db)
    return res

def exp_render_report(db, uid, object, ids, datas=None, context=None):
    if not datas:
        datas={}
    if not context:
        context={}

    self_id_protect.acquire()
    global self_id
    self_id += 1
    id = self_id
    self_id_protect.release()

    self_reports[id] = {'uid': uid, 'result': False, 'state': False, 'exception': None}

    cr = openerp.registry(db).cursor()
    try:
        result, format = openerp.report.render_report(cr, uid, ids, object, datas, context)
        if not result:
            tb = sys.exc_info()
            self_reports[id]['exception'] = openerp.exceptions.DeferredException('RML is not available at specified location or not enough data to print!', tb)
        self_reports[id]['result'] = result
        self_reports[id]['format'] = format
        self_reports[id]['state'] = True
    except Exception, exception:

        _logger.exception('Exception: %s\n', exception)
        if hasattr(exception, 'name') and hasattr(exception, 'value'):
            self_reports[id]['exception'] = openerp.exceptions.DeferredException(tools.ustr(exception.name), tools.ustr(exception.value))
        else:
            tb = sys.exc_info()
            self_reports[id]['exception'] = openerp.exceptions.DeferredException(tools.exception_to_unicode(exception), tb)
        self_reports[id]['state'] = True
    cr.commit()
    cr.close()

    return _check_report(id)

def exp_report(db, uid, object, ids, datas=None, context=None):
    if not datas:
        datas={}
    if not context:
        context={}

    self_id_protect.acquire()
    global self_id
    self_id += 1
    id = self_id
    self_id_protect.release()

    self_reports[id] = {'uid': uid, 'result': False, 'state': False, 'exception': None}

    def go(id, uid, ids, datas, context):
        with openerp.api.Environment.manage():
            cr = openerp.registry(db).cursor()
            try:
                result, format = openerp.report.render_report(cr, uid, ids, object, datas, context)
                if not result:
                    tb = sys.exc_info()
                    self_reports[id]['exception'] = openerp.exceptions.DeferredException('RML is not available at specified location or not enough data to print!', tb)
                self_reports[id]['result'] = result
                self_reports[id]['format'] = format
                self_reports[id]['state'] = True
            except Exception, exception:
                _logger.exception('Exception: %s\n', exception)
                if hasattr(exception, 'name') and hasattr(exception, 'value'):
                    self_reports[id]['exception'] = openerp.exceptions.DeferredException(tools.ustr(exception.name), tools.ustr(exception.value))
                else:
                    tb = sys.exc_info()
                    self_reports[id]['exception'] = openerp.exceptions.DeferredException(tools.exception_to_unicode(exception), tb)
                self_reports[id]['state'] = True
            cr.commit()
            cr.close()
        return True

    threading.Thread(target=go, args=(id, uid, ids, datas, context)).start()
    return id

def _check_report(report_id):
    result = self_reports[report_id]
    exc = result['exception']
    if exc:
        raise UserError('%s: %s' % (exc.message, exc.traceback))
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
        del self_reports[report_id]
    return res

def exp_report_get(db, uid, report_id):
    if report_id in self_reports:
        if self_reports[report_id]['uid'] == uid:
            return _check_report(report_id)
        else:
            raise Exception, 'AccessDenied'
    else:
        raise Exception, 'ReportNotFound'
