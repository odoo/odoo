# -*- coding: utf-8 -*-
import time

import openerp

class m(openerp.osv.osv.Model):
    """ This model exposes a few methods that will consume between 'almost no
        resource' and 'a lot of resource'.
    """
    _name = 'test.limits.model'

    def consume_nothing(self, cr, uid, context=None):
        return True

    def consume_memory(self, cr, uid, size, context=None):
        l = [0] * size
        return True

    def leak_memory(self, cr, uid, size, context=None):
        if not hasattr(self, 'l'):
            self.l = []
        self.l.append([0] * size)
        return True

    def consume_time(self, cr, uid, seconds, context=None):
        time.sleep(seconds)
        return True

    def consume_cpu_time(self, cr, uid, seconds, context=None):
        t0 = time.clock()
        t1 = time.clock()
        while t1 - t0 < seconds:
            for i in xrange(10000000):
                x = i * i
            t1 = time.clock()
        return True
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
