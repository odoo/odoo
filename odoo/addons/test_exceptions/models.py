# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.exceptions
import odoo.osv.osv
from odoo import models, api
from odoo.tools.safe_eval import safe_eval

class m(models.Model):
    """ This model exposes a few methods that will raise the different
        exceptions that must be handled by the server (and its RPC layer)
        and the clients.
    """
    _name = 'test.exceptions.model'
    _description = 'Test Exception Model'

    def generate_except_osv(self):
        # title is ignored in the new (6.1) exceptions
        raise odoo.osv.osv.except_osv('title', 'description')

    def generate_except_orm(self):
        # title is ignored in the new (6.1) exceptions
        raise odoo.exceptions.except_orm('title', 'description')

    def generate_warning(self):
        raise odoo.exceptions.Warning('description')

    def generate_redirect_warning(self):
        action = self.env.ref('test_exceptions.action_test_exceptions')
        raise odoo.exceptions.RedirectWarning('description', action.id, 'Go to the redirection')

    def generate_access_denied(self):
        raise odoo.exceptions.AccessDenied()

    def generate_access_error(self):
        raise odoo.exceptions.AccessError('description')

    def generate_exc_access_denied(self):
        raise Exception('AccessDenied')

    def generate_undefined(self):
        self.surely_undefined_symbol

    def generate_user_error(self):
        raise odoo.exceptions.UserError('description')

    def generate_missing_error(self):
        raise odoo.exceptions.MissingError('description')

    def generate_validation_error(self):
        raise odoo.exceptions.ValidationError('description')

    def generate_except_osv_safe_eval(self):
        self.generate_safe_eval(self.generate_except_osv)

    def generate_except_orm_safe_eval(self):
        self.generate_safe_eval(self.generate_except_orm)

    def generate_warning_safe_eval(self):
        self.generate_safe_eval(self.generate_warning)

    def generate_redirect_warning_safe_eval(self):
        self.generate_safe_eval(self.generate_redirect_warning)

    def generate_access_denied_safe_eval(self):
        self.generate_safe_eval(self.generate_access_denied)

    def generate_access_error_safe_eval(self):
        self.generate_safe_eval(self.generate_access_error)

    def generate_exc_access_denied_safe_eval(self):
        self.generate_safe_eval(self.generate_exc_access_denied)

    def generate_undefined_safe_eval(self):
        self.generate_safe_eval(self.generate_undefined)

    def generate_user_error_safe_eval(self):
        self.generate_safe_eval(self.generate_user_error)

    def generate_missing_error_safe_eval(self):
        self.generate_safe_eval(self.generate_missing_error)

    def generate_validation_error_safe_eval(self):
        self.generate_safe_eval(self.generate_validation_error)

    def generate_safe_eval(self, f):
        globals_dict = { 'generate': f }
        safe_eval("generate()", mode='exec', globals_dict=globals_dict)
