# -*- coding: utf-8 -*-
import openerp

class m(openerp.osv.osv.Model):
    """ This model exposes a few methods that will raise the different
        exceptions that must be handled by the server (and its RPC layer)
        and the clients.
    """
    _name = 'test.exceptions.model'

    def generate_except_osv(self, cr, uid, ids, context=None):
        # title is ignored in the new (6.1) exceptions
        raise openerp.osv.osv.except_osv('title', 'description')

    def generate_except_orm(self, cr, uid, ids, context=None):
        # title is ignored in the new (6.1) exceptions
        raise openerp.osv.orm.except_orm('title', 'description')

    def generate_warning(self, cr, uid, ids, context=None):
        raise openerp.exceptions.Warning('description')

    def generate_access_denied(self, cr, uid, ids, context=None):
        raise openerp.exceptions.AccessDenied()

    def generate_access_error(self, cr, uid, ids, context=None):
        raise openerp.exceptions.AccessError('description')

    def generate_exc_access_denied(self, cr, uid, ids, context=None):
        raise Exception('AccessDenied')

    def generate_undefined(self, cr, uid, ids, context=None):
        self.surely_undefined_sumbol
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
