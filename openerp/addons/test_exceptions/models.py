# -*- coding: utf-8 -*-
import openerp.exceptions
import openerp.osv.orm
import openerp.osv.osv
import openerp.tools.safe_eval

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

    def generate_redirect_warning(self, cr, uid, ids, context=None):
        dummy, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'test_exceptions', 'action_test_exceptions')
        raise openerp.exceptions.RedirectWarning('description', action_id, 'go to the redirection')

    def generate_access_denied(self, cr, uid, ids, context=None):
        raise openerp.exceptions.AccessDenied()

    def generate_access_error(self, cr, uid, ids, context=None):
        raise openerp.exceptions.AccessError('description')

    def generate_exc_access_denied(self, cr, uid, ids, context=None):
        raise Exception('AccessDenied')

    def generate_undefined(self, cr, uid, ids, context=None):
        self.surely_undefined_symbol


    def generate_except_osv_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_except_osv, context)

    def generate_except_orm_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_except_orm, context)

    def generate_warning_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_warning, context)

    def generate_redirect_warning_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_redirect_warning, context)

    def generate_access_denied_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_access_denied, context)

    def generate_access_error_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_access_error, context)

    def generate_exc_access_denied_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_exc_access_denied, context)

    def generate_undefined_safe_eval(self, cr, uid, ids, context=None):
        self.generate_safe_eval(cr, uid, ids, self.generate_undefined, context)


    def generate_safe_eval(self, cr, uid, ids, f, context):
        globals_dict = { 'generate': lambda *args: f(cr, uid, ids, context) }
        openerp.tools.safe_eval.safe_eval("generate()", mode='exec', globals_dict=globals_dict)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
