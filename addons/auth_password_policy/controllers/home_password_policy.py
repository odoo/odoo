from odoo.addons.web.controllers.home import Home
from odoo.http import request


class HomePasswordPolicy(Home):

    def _prepare_change_password_layout_values(self):
        """ To enable HTML verification of the new password's min length according the value specified in the settings. """
        values = super()._prepare_change_password_layout_values()
        values['password_minimum_length'] = request.env['ir.config_parameter'].sudo().get_param('auth_password_policy.minlength')
        return values
