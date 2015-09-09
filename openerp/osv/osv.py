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

#.apidoc title: Objects Services (OSV)

from functools import wraps
import logging
from psycopg2 import IntegrityError, OperationalError, errorcodes

import orm
import openerp
import openerp.netsvc as netsvc
import openerp.pooler as pooler
import openerp.sql_db as sql_db
from openerp.tools.translate import translate
from openerp.osv.orm import MetaModel, Model, TransientModel, AbstractModel
import openerp.exceptions

import time
import random

_logger = logging.getLogger(__name__)

PG_CONCURRENCY_ERRORS_TO_RETRY = (errorcodes.LOCK_NOT_AVAILABLE, errorcodes.SERIALIZATION_FAILURE, errorcodes.DEADLOCK_DETECTED)
MAX_TRIES_ON_CONCURRENCY_FAILURE = 5

# Deprecated.
class except_osv(Exception):
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.args = (name, value)

service = None

class object_proxy(object):
    def __init__(self):
        global service
        service = self

    def check(f):
        @wraps(f)
        def wrapper(self, dbname, *args, **kwargs):
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
                            obj = self.get(args[1])
                            if len(args) > 3 and isinstance(args[3], (long, int, list)):
                                ids = args[3]
                            else:
                                ids = []
                        cr = sql_db.db_connect(dbname).cursor()
                        return src(obj, cr, uid, ids, context=(ctx or {}))
                    except Exception:
                        pass
                    finally:
                        if cr: cr.close()

                    return False # so that the original SQL error will
                                 # be returned, it is the best we have.

                try:
                    cr = sql_db.db_connect(dbname).cursor()
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
                    if pooler.get_pool(dbname)._init:
                        raise except_osv('Database not ready', 'Currently, this database is not fully loaded and can not be used.')
                    return f(self, dbname, *args, **kwargs)
                except OperationalError, e:
                    # Automatically retry the typical transaction serialization errors
                    if e.pgcode not in PG_CONCURRENCY_ERRORS_TO_RETRY:
                        raise
                    if tries >= MAX_TRIES_ON_CONCURRENCY_FAILURE:
                        _logger.warning("%s, maximum number of tries reached" % errorcodes.lookup(e.pgcode))
                        raise
                    wait_time = random.uniform(0.0, 2 ** tries)
                    tries += 1
                    _logger.info("%s, retrying %d/%d in %.04f sec..." % (errorcodes.lookup(e.pgcode), tries, MAX_TRIES_ON_CONCURRENCY_FAILURE, wait_time))
                    time.sleep(wait_time)
                except orm.except_orm, inst:
                    raise except_osv(inst.name, inst.value)
                except except_osv:
                    raise
                except IntegrityError, inst:
                    osv_pool = pooler.get_pool(dbname)
                    for key in osv_pool._sql_error.keys():
                        if key in inst[0]:
                            netsvc.abort_response(1, _('Constraint Error'), 'warning',
                                            tr(osv_pool._sql_error[key], 'sql_constraint') or inst[0])
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
                        netsvc.abort_response(1, _('Integrity Error'), 'warning', msg)
                    else:
                        netsvc.abort_response(1, _('Integrity Error'), 'warning', inst[0])
                except Exception:
                    _logger.exception("Uncaught exception")
                    raise

        return wrapper

    def execute_cr(self, cr, uid, obj, method, *args, **kw):
        object = pooler.get_pool(cr.dbname).get(obj)
        if not object:
            raise except_osv('Object Error', 'Object %s doesn\'t exist' % str(obj))
        return getattr(object, method)(cr, uid, *args, **kw)

    def execute_kw(self, db, uid, obj, method, args, kw=None):
        return self.execute(db, uid, obj, method, *args, **kw or {})

    @check
    def execute(self, db, uid, obj, method, *args, **kw):
        cr = pooler.get_db(db).cursor()
        try:
            try:
                if method.startswith('_'):
                    raise except_osv('Access Denied', 'Private methods (such as %s) cannot be called remotely.' % (method,))
                res = self.execute_cr(cr, uid, obj, method, *args, **kw)
                if res is None:
                    _logger.warning('The method %s of the object %s can not return `None` !', method, obj)
                cr.commit()
            except Exception:
                cr.rollback()
                raise
        finally:
            cr.close()
        return res

    def exec_workflow_cr(self, cr, uid, obj, method, *args):
        wf_service = netsvc.LocalService("workflow")
        return wf_service.trg_validate(uid, obj, args[0], method, cr)

    @check
    def exec_workflow(self, db, uid, obj, method, *args):
        cr = pooler.get_db(db).cursor()
        try:
            try:
                res = self.exec_workflow_cr(cr, uid, obj, method, *args)
                cr.commit()
            except Exception:
                cr.rollback()
                raise
        finally:
            cr.close()
        return res

# deprecated - for backward compatibility.
osv = Model
osv_memory = TransientModel
osv_abstract = AbstractModel # ;-)


def start_object_proxy():
    object_proxy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

