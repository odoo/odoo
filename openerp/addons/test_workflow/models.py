# -*- coding: utf-8 -*-
import logging

import openerp.osv.orm

_logger = logging.getLogger(__name__)

class m(openerp.osv.orm.Model):
    """ A model for which we will define a workflow (see data.xml). """
    _name = 'test.workflow.model'

    def print_(self, cr, uid, ids, s, context=None):
        _logger.info('Running activity `%s` for record %s', s, ids)
        return True

    def print_a(self, cr, uid, ids, context=None):
        return self.print_(cr, uid, ids, 'a', context)

    def print_b(self, cr, uid, ids, context=None):
        return self.print_(cr, uid, ids, 'b', context)

    def print_c(self, cr, uid, ids, context=None):
        return self.print_(cr, uid, ids, 'c', context)

    def condition(self, cr, uid, ids, context=None):
        m = self.pool['test.workflow.trigger']
        for r in m.browse(cr, uid, [1], context=context):
            if not r.value:
                return False
        return True

    def trigger(self, cr, uid, context=None):
        return openerp.workflow.trg_trigger(uid, 'test.workflow.trigger', 1, cr)

class n(openerp.osv.orm.Model):
    """ A model used for the trigger feature. """
    _name = 'test.workflow.trigger'
    _columns = { 'value': openerp.osv.fields.boolean('Value') }
    _defaults = { 'value': False }

class a(openerp.osv.orm.Model):
    _name = 'test.workflow.model.a'
    _columns = { 'value': openerp.osv.fields.integer('Value') }
    _defaults = { 'value': 0 }

class b(openerp.osv.orm.Model):
    _name = 'test.workflow.model.b'
    _inherit = 'test.workflow.model.a'

class c(openerp.osv.orm.Model):
    _name = 'test.workflow.model.c'
    _inherit = 'test.workflow.model.a'

class d(openerp.osv.orm.Model):
    _name = 'test.workflow.model.d'
    _inherit = 'test.workflow.model.a'

class e(openerp.osv.orm.Model):
    _name = 'test.workflow.model.e'
    _inherit = 'test.workflow.model.a'

for name in 'bcdefghijkl':
    #
    # Do not use type() to create the class here, but use the class construct.
    # This is because the __module__ of the new class would be the one of the
    # metaclass that provides method __new__!
    #
    class NewModel(openerp.osv.orm.Model):
        _name = 'test.workflow.model.%s' % name
        _inherit = 'test.workflow.model.a'
