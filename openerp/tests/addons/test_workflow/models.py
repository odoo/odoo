# -*- coding: utf-8 -*-
import openerp

class m(openerp.osv.orm.Model):
    """ A model for which we will define a worflow (see data.xml). """
    _name = 'test.workflow.model'

    def print_(self, cr, uid, ids, s, context=None):
        print '  Running activity `%s` for record %s' % (s, ids)
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
