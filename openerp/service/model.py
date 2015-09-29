# -*- coding: utf-8 -*-

from functools import wraps
import logging
from psycopg2 import IntegrityError, OperationalError, errorcodes
import random
import threading
import time

import openerp
from openerp.exceptions import UserError, ValidationError, QWebException
from openerp.tools.translate import translate
from openerp.tools.translate import _

import security

_logger = logging.getLogger(__name__)

PG_CONCURRENCY_ERRORS_TO_RETRY = (errorcodes.LOCK_NOT_AVAILABLE, errorcodes.SERIALIZATION_FAILURE, errorcodes.DEADLOCK_DETECTED)
MAX_TRIES_ON_CONCURRENCY_FAILURE = 5

def dispatch(method, params):
    (db, uid, passwd ) = params[0:3]

    # set uid tracker - cleaned up at the WSGI
    # dispatching phase in openerp.service.wsgi_server.application
    threading.current_thread().uid = uid

    params = params[3:]
    if method == 'obj_list':
        raise NameError("obj_list has been discontinued via RPC as of 6.0, please query ir.model directly!")
    if method not in ['execute', 'execute_kw', 'exec_workflow']:
        raise NameError("Method not available %s" % method)
    security.check(db,uid,passwd)
    openerp.modules.registry.RegistryManager.check_registry_signaling(db)
    fn = globals()[method]
    res = fn(db, uid, *params)
    openerp.modules.registry.RegistryManager.signal_caches_change(db)
    return res

def check(f):
    @wraps(f)
    def wrapper(___dbname, *args, **kwargs):
        """ Wraps around OSV functions and normalises a few exceptions
        """
        dbname = ___dbname      # NOTE: this forbid to use "___dbname" as arguments in http routes

        def tr(src, ttype):
            # We try to do the same as the _(), but without the frame
            # inspection, since we aready are wrapping an osv function
            # trans_obj = self.get('ir.translation') cannot work yet :(
            ctx = {}
            if not kwargs:
                if args and isinstance(args[-1], dict):
                    ctx = args[-1]
            elif isinstance(kwargs, dict):
                ctx = kwargs.get('context', {})

            uid = 1
            if args and isinstance(args[0], (long, int)):
                uid = args[0]

            lang = ctx and ctx.get('lang')
            if not (lang or hasattr(src, '__call__')):
                return src

            # We open a *new* cursor here, one reason is that failed SQL
            # queries (as in IntegrityError) will invalidate the current one.
            cr = False

            if hasattr(src, '__call__'):
                # callable. We need to find the right parameters to call
                # the  orm._sql_message(self, cr, uid, ids, context) function,
                # or we skip..
                # our signature is f(registry, dbname [,uid, obj, method, args])
                try:
                    if args and len(args) > 1:
                        # TODO self doesn't exist, but was already wrong before (it was not a registry but just the object_service.
                        obj = self.get(args[1])
                        if len(args) > 3 and isinstance(args[3], (long, int, list)):
                            ids = args[3]
                        else:
                            ids = []
                    cr = openerp.sql_db.db_connect(dbname).cursor()
                    return src(obj, cr, uid, ids, context=(ctx or {}))
                except Exception:
                    pass
                finally:
                    if cr: cr.close()

                return False # so that the original SQL error will
                             # be returned, it is the best we have.

            try:
                cr = openerp.sql_db.db_connect(dbname).cursor()
                res = translate(cr, name=False, source_type=ttype,
                                lang=lang, source=src)
                if res:
                    return res
                else:
                    return src
            finally:
                if cr: cr.close()

        def _(src):
            return tr(src, 'code')

        tries = 0
        while True:
            try:
                if openerp.registry(dbname)._init and not openerp.tools.config['test_enable']:
                    raise openerp.exceptions.Warning('Currently, this database is not fully loaded and can not be used.')
                return f(dbname, *args, **kwargs)
            except (OperationalError, QWebException) as e:
                if isinstance(e, QWebException):
                    cause = e.qweb.get('cause')
                    if isinstance(cause, OperationalError):
                        e = cause
                    else:
                        raise
                # Automatically retry the typical transaction serialization errors
                if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                    raise
                if tries >= MAX_TRIES_ON_CONCURRENCY_FAILURE:
                    _logger.info("%s, maximum number of tries reached" % errorcodes.lookup(e.pgcode))
                    raise
                wait_time = random.uniform(0.0, 2 ** tries)
                tries += 1
                _logger.info("%s, retry %d/%d in %.04f sec..." % (errorcodes.lookup(e.pgcode), tries, MAX_TRIES_ON_CONCURRENCY_FAILURE, wait_time))
                time.sleep(wait_time)
            except IntegrityError, inst:
                registry = openerp.registry(dbname)
                for key in registry._sql_error.keys():
                    if key in inst[0]:
                        raise ValidationError(tr(registry._sql_error[key], 'sql_constraint') or inst[0])
                if inst.pgcode in (errorcodes.NOT_NULL_VIOLATION, errorcodes.FOREIGN_KEY_VIOLATION, errorcodes.RESTRICT_VIOLATION):
                    msg = _('The operation cannot be completed, probably due to the following:\n- deletion: you may be trying to delete a record while other records still reference it\n- creation/update: a mandatory field is not correctly set')
                    _logger.debug("IntegrityError", exc_info=True)
                    try:
                        errortxt = inst.pgerror.replace('«','"').replace('»','"')
                        if '"public".' in errortxt:
                            context = errortxt.split('"public".')[1]
                            model_name = table = context.split('"')[1]
                        else:
                            last_quote_end = errortxt.rfind('"')
                            last_quote_begin = errortxt.rfind('"', 0, last_quote_end)
                            model_name = table = errortxt[last_quote_begin+1:last_quote_end].strip()
                        model = table.replace("_",".")
                        if model in registry:
                            model_obj = registry[model]
                            model_name = model_obj._description or model_obj._name
                        msg += _('\n\n[object with reference: %s - %s]') % (model_name, model)
                    except Exception:
                        pass
                    raise ValidationError(msg)
                else:
                    raise ValidationError(inst[0])

    return wrapper

def execute_cr(cr, uid, obj, method, *args, **kw):
    object = openerp.registry(cr.dbname).get(obj)
    if object is None:
        raise UserError(_("Object %s doesn't exist") % obj)
    return getattr(object, method)(cr, uid, *args, **kw)

def execute_kw(db, uid, obj, method, args, kw=None):
    return execute(db, uid, obj, method, *args, **kw or {})

@check
def execute(db, uid, obj, method, *args, **kw):
    threading.currentThread().dbname = db
    with openerp.registry(db).cursor() as cr:
        if method.startswith('_'):
            raise UserError(_('Private methods (such as %s) cannot be called remotely.') % (method,))
        res = execute_cr(cr, uid, obj, method, *args, **kw)
        if res is None:
            _logger.info('The method %s of the object %s can not return `None` !', method, obj)
        return res

def exec_workflow_cr(cr, uid, obj, signal, *args):
    res_id = args[0]
    return execute_cr(cr, uid, obj, 'signal_workflow', [res_id], signal)[res_id]


@check
def exec_workflow(db, uid, obj, signal, *args):
    with openerp.registry(db).cursor() as cr:
        return exec_workflow_cr(cr, uid, obj, signal, *args)
