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

import orm
import openerp
import openerp.netsvc as netsvc
import openerp.pooler as pooler
import openerp.sql_db as sql_db
import logging
from psycopg2 import IntegrityError, errorcodes
from openerp.tools.config import config
from openerp.tools.func import wraps
from openerp.tools.translate import translate
from openerp.osv.orm import MetaModel, Model


class except_osv(Exception):
    def __init__(self, name, value, exc_type='warning'):
        self.name = name
        self.exc_type = exc_type
        self.value = value
        self.args = (exc_type, name)


class object_proxy(netsvc.Service):
    def __init__(self):
        self.logger = logging.getLogger('web-services')
        netsvc.Service.__init__(self, 'object_proxy', audience='')
        self.exportMethod(self.exec_workflow)
        self.exportMethod(self.execute)

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

            try:
                if pooler.get_pool(dbname)._init:
                    raise except_osv('Database not ready', 'Currently, this database is not fully loaded and can not be used.')
                return f(self, dbname, *args, **kwargs)
            except orm.except_orm, inst:
                if inst.name == 'AccessError':
                    self.logger.debug("AccessError", exc_info=True)
                self.abortResponse(1, inst.name, 'warning', inst.value)
            except except_osv, inst:
                self.abortResponse(1, inst.name, inst.exc_type, inst.value)
            except IntegrityError, inst:
                osv_pool = pooler.get_pool(dbname)
                for key in osv_pool._sql_error.keys():
                    if key in inst[0]:
                        self.abortResponse(1, _('Constraint Error'), 'warning',
                                        tr(osv_pool._sql_error[key], 'sql_constraint') or inst[0])
                if inst.pgcode in (errorcodes.NOT_NULL_VIOLATION, errorcodes.FOREIGN_KEY_VIOLATION, errorcodes.RESTRICT_VIOLATION):
                    msg = _('The operation cannot be completed, probably due to the following:\n- deletion: you may be trying to delete a record while other records still reference it\n- creation/update: a mandatory field is not correctly set')
                    self.logger.debug("IntegrityError", exc_info=True)
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
                    self.abortResponse(1, _('Integrity Error'), 'warning', msg)
                else:
                    self.abortResponse(1, _('Integrity Error'), 'warning', inst[0])
            except Exception:
                self.logger.exception("Uncaught exception")
                raise

        return wrapper

    def execute_cr(self, cr, uid, obj, method, *args, **kw):
        object = pooler.get_pool(cr.dbname).get(obj)
        if not object:
            raise except_osv('Object Error', 'Object %s doesn\'t exist' % str(obj))
        return getattr(object, method)(cr, uid, *args, **kw)

    @check
    def execute(self, db, uid, obj, method, *args, **kw):
        cr = pooler.get_db(db).cursor()
        try:
            try:
                if method.startswith('_'):
                    raise except_osv('Access Denied', 'Private methods (such as %s) cannot be called remotely.' % (method,))
                res = self.execute_cr(cr, uid, obj, method, *args, **kw)
                if res is None:
                    self.logger.warning('The method %s of the object %s can not return `None` !', method, obj)
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


class TransientModel(Model):
    """ Model for transient records.

    A TransientModel works similarly to a regular Model but the assiociated
    records will be cleaned automatically from the database after some time.

    A TransientModel has no access rules.

    """
    __metaclass__ = MetaModel
    _register = False # Set to false if the model shouldn't be automatically discovered.
    _transient = True
    _max_count = None
    _max_hours = None
    _check_time = 20

    def __init__(self, pool, cr):
        super(TransientModel, self).__init__(pool, cr)
        self.check_count = 0
        self._max_count = config.get('osv_memory_count_limit')
        self._max_hours = config.get('osv_memory_age_limit')
        cr.execute('delete from wkf_instance where res_type=%s', (self._name,))

    def _clean_transient_rows_older_than(self, cr, seconds):
        if not self._log_access:
            self.logger = logging.getLogger('orm').warning(
                "Transient model without write_date: %s" % (self._name,))
            return

        cr.execute("SELECT id FROM " + self._table + " WHERE"
            " COALESCE(write_date, create_date, now())::timestamp <"
            " (now() - interval %s)", ("%s seconds" % seconds,))
        ids = [x[0] for x in cr.fetchall()]
        self.unlink(cr, openerp.SUPERUSER, ids)

    def _clean_old_transient_rows(self, cr, count):
        if not self._log_access:
            self.logger = logging.getLogger('orm').warning(
                "Transient model without write_date: %s" % (self._name,))
            return

        cr.execute(
            "SELECT id, COALESCE(write_date, create_date, now())::timestamp"
            " AS t FROM " + self._table +
            " ORDER BY t LIMIT %s", (count,))
        ids = [x[0] for x in cr.fetchall()]
        self.unlink(cr, openerp.SUPERUSER, ids)

    def vacuum(self, cr, uid, force=False):
        """ Clean the TransientModel records.

        This unlinks old records from the transient model tables whenever the
        "_max_count" or "_max_age" conditions (if any) are reached.
        Actual cleaning will happen only once every "_check_time" calls.
        This means this method can be called frequently called (e.g. whenever
        a new record is created).
        """
        self.check_count += 1
        if (not force) and (self.check_count % self._check_time):
            self.check_count = 0
            return True

        # Age-based expiration
        if self._max_hours:
            self._clean_transient_rows_older_than(cr, self._max_hours * 60 * 60)

        # Count-based expiration
        if self._max_count:
            self._clean_old_transient_rows(cr, self._max_count)

        return True

    def check_access_rule(self, cr, uid, ids, operation, context=None):
        # No access rules for transient models.
        if self._log_access and uid != openerp.SUPERUSER:
            cr.execute("SELECT distinct create_uid FROM " + self._table + " WHERE"
                " id IN %s", (tuple(ids),))
            uids = [x[0] for x in cr.fetchall()]
            if len(uids) != 1 or uids[0] != uid:
                raise orm.except_orm(_('AccessError'), '%s access is '
                    'restricted to your own records for transient models '
                    '(except for the super-user).' % mode.capitalize())

    def create(self, cr, uid, vals, context=None):
        self.vacuum(cr, uid)
        return super(TransientModel, self).create(cr, uid, vals, context)

    def _search(self, cr, uid, domain, offset=0, limit=None, order=None, context=None, count=False, access_rights_uid=None):

        # Restrict acces to the current user, except for the super-user.
        if self._log_access and uid != openerp.SUPERUSER:
            import expression
            domain = expression.expression_and(('create_uid', '=', uid), domain)

        # TODO unclear: shoudl access_rights_uid be set to None (effectively ignoring it) or used instead of uid?
        return super(TransientModel, self)._search(cr, uid, domain, offset, limit, order, context, count, access_rights_uid)


# For backward compatibility.
osv = Model
osv_memory = TransientModel


def start_object_proxy():
    object_proxy()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

