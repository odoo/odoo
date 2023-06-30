# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError

class View(models.Model):
    _inherit = 'ir.ui.view'

    @api.constrains('active')
    def _check_auth_signup_view(self):
        if self.filtered(lambda v: v.xml_id == 'auth_signup.signup' and not v.active):
            raise UserError(_("You cannot deactivate the Sign up login view."))

    def unlink(self):
        if self.filtered(lambda v: v.xml_id == 'auth_signup.signup'):
            raise UserError(_("You cannot delete the Sign up login view."))
        return super().unlink()
