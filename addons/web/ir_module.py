from openerp.osv import osv
import openerp.wsgi.core as oewsgi

from common.http import Root

class ir_module(osv.Model):
    _inherit = 'ir.module.module'

    def update_list(self, cr, uid, context=None):
        result = super(ir_module, self).update_list(cr, uid, context=context)

        if tuple(result) != (0, 0):
            for handler in oewsgi.module_handlers:
                if isinstance(handler, Root):
                    handler._load_addons()

        return result
