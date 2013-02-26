# -*- coding: utf-8 -*-

from functools import wraps
import logging
from psycopg2 import IntegrityError, errorcodes
import threading

import openerp
from openerp.tools.translate import translate
from openerp.osv.orm import except_orm

import security

_logger = logging.getLogger(__name__)

def dispatch(method, params):
    (db, uid, passwd ) = params[0:3]
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
    def wrapper(dbname, *args, **kwargs):
        """ Wraps around OSV functions and normalises a few exceptions
        """

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
                # our signature is f(osv_pool, dbname [,uid, obj, method, args])
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

        try:
            if openerp.pooler.get_pool(dbname)._init:
                raise openerp.exceptions.Warning('Currently, this database is not fully loaded and can not be used.')
            return f(dbname, *args, **kwargs)
        except IntegrityError, inst:
            osv_pool = openerp.pooler.get_pool(dbname)
            for key in osv_pool._sql_error.keys():
                if key in inst[0]:
                    raise openerp.osv.orm.except_orm(_('Constraint Error'), tr(osv_pool._sql_error[key], 'sql_constraint') or inst[0])
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
                    model_obj = osv_pool.get(model)
                    if model_obj:
                        model_name = model_obj._description or model_obj._name
                    msg += _('\n\n[object with reference: %s - %s]') % (model_name, model)
                except Exception:
                    pass
                raise openerp.osv.orm.except_orm(_('Integrity Error'), msg)
            else:
                raise openerp.osv.orm.except_orm(_('Integrity Error'), inst[0])

    return wrapper

def execute_cr(cr, uid, obj, method, *args, **kw):
    object = openerp.pooler.get_pool(cr.dbname).get(obj)
    if not object:
        raise except_orm('Object Error', 'Object %s doesn\'t exist' % str(obj))
    return getattr(object, method)(cr, uid, *args, **kw)

def execute_kw(db, uid, obj, method, args, kw=None):
    return execute(db, uid, obj, method, *args, **kw or {})

@check
def execute(db, uid, obj, method, *args, **kw):
    threading.currentThread().dbname = db
    cr = openerp.pooler.get_db(db).cursor()
    try:
        try:
            if method.startswith('_'):
                raise except_orm('Access Denied', 'Private methods (such as %s) cannot be called remotely.' % (method,))
            res = execute_cr(cr, uid, obj, method, *args, **kw)
            if res is None:
                _logger.warning('The method %s of the object %s can not return `None` !', method, obj)
            cr.commit()
        except Exception:
            cr.rollback()
            raise
    finally:
        cr.close()
    return res

def exec_workflow_cr(cr, uid, obj, signal, *args):
    object = openerp.pooler.get_pool(cr.dbname).get(obj)
    if not object:
        raise except_orm('Object Error', 'Object %s doesn\'t exist' % str(obj))
    res_id = args[0]
    return object.signal_workflow(cr, uid, [res_id], signal)[res_id]

@check
def exec_workflow(db, uid, obj, signal, *args):
    cr = openerp.pooler.get_db(db).cursor()
    try:
        try:
            res = exec_workflow_cr(cr, uid, obj, signal, *args)
            cr.commit()
        except Exception:
            cr.rollback()
            raise
    finally:
        cr.close()
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
