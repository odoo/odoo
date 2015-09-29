# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import openerp

class osv_memory_autovacuum(openerp.osv.osv.osv_memory):
    """ Expose the osv_memory.vacuum() method to the cron jobs mechanism. """
    _name = 'osv_memory.autovacuum'

    def power_on(self, cr, uid, context=None):
        for model in self.pool.models.values():
            if model.is_transient():
                model._transient_vacuum(cr, uid, force=True)
        return True
