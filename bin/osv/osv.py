# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
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

#
# OSV: Objects Services
#

import orm
import netsvc
import pooler
import copy
import sys

from psycopg2 import IntegrityError
from netsvc import Logger, LOG_ERROR
from tools.misc import UpdateableDict

module_list = []
module_class_list = {}
class_pool = {}


class except_osv(Exception):
    def __init__(self, name, value, exc_type='warning'):
        self.name = name
        self.exc_type = exc_type
        self.value = value
        self.args = (exc_type, name)


class osv_pool(netsvc.Service):

    def __init__(self):
        self.obj_pool = {}
        self.module_object_list = {}
        self.created = []
        self._sql_error = {}
        self._store_function = {}
        self._init = True
        self._init_parent = {}
        netsvc.Service.__init__(self, 'object_proxy', audience='')
        self.joinGroup('web-services')
        self.exportMethod(self.exportedMethods)
        self.exportMethod(self.obj_list)
        self.exportMethod(self.exec_workflow)
        self.exportMethod(self.execute)
        self.exportMethod(self.execute_cr)

    def init_set(self, cr, mode):
        if mode <> self._init:
            if mode:
                self._init_parent = {}
            if not mode:
                for o in self._init_parent:
                    self.get(o)._parent_store_compute(cr)
            self._init = mode
            return True
        return False

    def execute_cr(self, cr, uid, obj, method, *args, **kw):
        try:
            object = pooler.get_pool(cr.dbname).get(obj)
            if not object:
                self.abortResponse(1, 'Object Error', 'warning',
                'Object %s doesn\'t exist' % str(obj))
            return getattr(object, method)(cr, uid, *args, **kw)
        except orm.except_orm, inst:
            self.abortResponse(1, inst.name, 'warning', inst.value)
        except except_osv, inst:
            self.abortResponse(1, inst.name, inst.exc_type, inst.value)
        except IntegrityError, inst:
            for key in self._sql_error.keys():
                if key in inst[0]:
                    self.abortResponse(1, 'Constraint Error', 'warning', self._sql_error[key])
            self.abortResponse(1, 'Integrity Error', 'warning', inst[0])
        except Exception, e:
            import traceback
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception( sys.exc_type, sys.exc_value, sys.exc_traceback))
            logger = Logger()
            for idx, s in enumerate(tb_s.split('\n')):
                logger.notifyChannel("web-services", LOG_ERROR, '[%2d]: %s' % (idx, s,))
            raise

    def execute(self, db, uid, obj, method, *args, **kw):
        db, pool = pooler.get_db_and_pool(db)
        cr = db.cursor()
        try:
            try:
                res = pool.execute_cr(cr, uid, obj, method, *args, **kw)
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

    def exec_workflow(self, db, uid, obj, method, *args):
        cr = pooler.get_db(db).cursor()
        try:
            try:
                res = self.exec_workflow_cr(cr, uid, obj, method, *args)
                cr.commit()
            except orm.except_orm, inst:
                cr.rollback()
                self.abortResponse(1, inst.name, 'warning', inst.value)
            except except_osv, inst:
                cr.rollback()
                self.abortResponse(1, inst.name, inst[0], inst.value)
        finally:
            cr.close()
        return res

    def obj_list(self):
        return self.obj_pool.keys()

    # adds a new object instance to the object pool.
    # if it already existed, the instance is replaced
    def add(self, name, obj_inst):
        if name in self.obj_pool:
            del self.obj_pool[name]
        self.obj_pool[name] = obj_inst

        module = str(obj_inst.__class__)[6:]
        module = module[:len(module)-1]
        module = module.split('.')[0][2:]
        self.module_object_list.setdefault(module, []).append(obj_inst)

    # Return False if object does not exist
    def get(self, name):
        obj = self.obj_pool.get(name, None)
        return obj

    #TODO: pass a list of modules to load
    def instanciate(self, module, cr):
        res = []
        class_list = module_class_list.get(module, [])
        for klass in class_list:
            res.append(klass.createInstance(self, module, cr))
        return res


class osv_memory(orm.orm_memory):
    #__metaclass__ = inheritor
    def __new__(cls):
        module = str(cls)[6:]
        module = module[:len(module)-1]
        module = module.split('.')[0][2:]
        if not hasattr(cls, '_module'):
            cls._module = module
        module_class_list.setdefault(cls._module, []).append(cls)
        class_pool[cls._name] = cls
        if module not in module_list:
            module_list.append(cls._module)
        return None

    #
    # Goal: try to apply inheritancy at the instanciation level and
    #       put objects in the pool var
    #
    def createInstance(cls, pool, module, cr):
        name = hasattr(cls, '_name') and cls._name or cls._inherit
        parent_name = hasattr(cls, '_inherit') and cls._inherit
        if parent_name:
            print 'Inherit not supported in osv_memory object !'
        obj = object.__new__(cls)
        obj.__init__(pool, cr)
        return obj
    createInstance = classmethod(createInstance)

    def __init__(self, pool, cr):
        pool.add(self._name, self)
        self.pool = pool
        orm.orm_memory.__init__(self, cr)



class osv(orm.orm):
    #__metaclass__ = inheritor
    def __new__(cls):
        module = str(cls)[6:]
        module = module[:len(module)-1]
        module = module.split('.')[0][2:]
        if not hasattr(cls, '_module'):
            cls._module = module
        module_class_list.setdefault(cls._module, []).append(cls)
        class_pool[cls._name] = cls
        if module not in module_list:
            module_list.append(cls._module)
        return None

    #
    # Goal: try to apply inheritancy at the instanciation level and
    #       put objects in the pool var
    #
    def createInstance(cls, pool, module, cr):
        parent_name = hasattr(cls, '_inherit') and cls._inherit
        if parent_name:
            parent_class = pool.get(parent_name).__class__
            assert pool.get(parent_name), "parent class %s does not exist in module %s !" % (parent_name, module)
            nattr = {}
            for s in ('_columns', '_defaults', '_inherits', '_constraints', '_sql_constraints'):
                new = copy.copy(getattr(pool.get(parent_name), s))
                if hasattr(new, 'update'):
                    new.update(cls.__dict__.get(s, {}))
                else:
                    if s=='_constraints':
                        for c in cls.__dict__.get(s, []):
                            exist = False
                            for c2 in range(len(new)):
                                if new[c2][2]==c[2]:
                                    new[c2] = c
                                    exist = True
                                    break
                            if not exist:
                                new.append(c)
                    else:
                        new.extend(cls.__dict__.get(s, []))
                nattr[s] = new
            name = hasattr(cls, '_name') and cls._name or cls._inherit
            cls = type(name, (cls, parent_class), nattr)
        obj = object.__new__(cls)
        obj.__init__(pool, cr)
        return obj
    createInstance = classmethod(createInstance)

    def __init__(self, pool, cr):
        pool.add(self._name, self)
        self.pool = pool
        orm.orm.__init__(self, cr)


class Cacheable(object):

    _cache = UpdateableDict()

    def add(self, key, value):
        self._cache[key] = value

    def invalidate(self, key):
        del self._cache[key]

    def get(self, key):
        try:
            w = self._cache[key]
            return w
        except KeyError:
            return None

    def clear(self):
        self._cache.clear()
        self._items = []


def filter_dict(d, fields):
    res = {}
    for f in fields + ['id']:
        if f in d:
            res[f] = d[f]
    return res


class cacheable_osv(osv, Cacheable):

    _relevant = ['lang']

    def __init__(self):
        super(cacheable_osv, self).__init__()

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        if not fields:
            fields = []
        if not context:
            context = {}
        fields = fields or self._columns.keys()
        ctx = [context.get(x, False) for x in self._relevant]
        result, tofetch = [], []
        for id in ids:
            res = self.get(self._name, id, ctx)
            if not res:
                tofetch.append(id)
            else:
                result.append(filter_dict(res, fields))

        # gen the list of "local" (ie not inherited) fields which are classic or many2one
        nfields = filter(lambda x: x[1]._classic_write, self._columns.items())
        # gen the list of inherited fields
        inherits = map(lambda x: (x[0], x[1][2]), self._inherit_fields.items())
        # complete the field list with the inherited fields which are classic or many2one
        nfields += filter(lambda x: x[1]._classic_write, inherits)
        nfields = [x[0] for x in nfields]

        res = super(cacheable_osv, self).read(cr, user, tofetch, nfields, context, load)
        for r in res:
            self.add((self._name, r['id'], ctx), r)
            result.append(filter_dict(r, fields))

        # Appel de fonction si necessaire
        tofetch = []
        for f in fields:
            if f not in nfields:
                tofetch.append(f)
        for f in tofetch:
            fvals = self._columns[f].get(cr, self, ids, f, user, context=context)
            for r in result:
                r[f] = fvals[r['id']]

        # TODO: tri par self._order !!
        return result

    def invalidate(self, key):
        del self._cache[key[0]][key[1]]

    def write(self, cr, user, ids, values, context=None):
        if not context:
            context = {}
        for id in ids:
            self.invalidate((self._name, id))
        return super(cacheable_osv, self).write(cr, user, ids, values, context)

    def unlink(self, cr, user, ids):
        self.clear()
        return super(cacheable_osv, self).unlink(cr, user, ids)

#cacheable_osv = osv


#class FakePool(object):
#   def __init__(self, module):
#       self.preferred_module = module

#   def get(self, name):
#       localpool = module_objects_dict.get(self.preferred_module, {'dict': {}})['dict']
#       if name in localpool:
#           obj = localpool[name]
#       else:
#           obj = pooler.get_pool(cr.dbname).get(name)
#       return obj

#       fake_pool = self
#       class fake_class(obj.__class__):
#           def __init__(self):
#               super(fake_class, self).__init__()
#               self.pool = fake_pool

#       return fake_class()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

