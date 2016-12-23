# -*- coding: utf-8 -*-
import datetime
from openerp.osv import orm, fields


class TestFunctionCounter(orm.Model):
    _name = 'test.function.counter'

    def _compute_cnt(self, cr, uid, ids, fname, arg, context=None):
        res = {}
        for cnt in self.browse(cr, uid, ids, context=context):
            res[cnt.id] = cnt.access and cnt.cnt+1 or 0
        return res

    _columns = {
        'access': fields.datetime('Datetime Field'),
        'cnt': fields.function(
            _compute_cnt, type='integer', string='Function Field', store=True),
    }


class TestFunctionNoInfiniteRecursion(orm.Model):
    _name = 'test.function.noinfiniterecursion'

    def _compute_f1(self, cr, uid, ids, fname, arg, context=None):
        res = {}
        for tf in self.browse(cr, uid, ids, context=context):
            res[tf.id] = 'create' in tf.f0 and 'create' or 'write'
        cntobj = self.pool['test.function.counter']
        cnt_id = self.pool['ir.model.data'].xmlid_to_res_id(
            cr, uid, 'test_function_oldapi.c1')
        cntobj.write(
            cr, uid, cnt_id, {'access': datetime.datetime.now()},
            context=context)
        return res

    _columns = {
        'f0': fields.char('Char Field'),
        'f1': fields.function(
            _compute_f1, type='char', string='Function Field', store=True),
    }
