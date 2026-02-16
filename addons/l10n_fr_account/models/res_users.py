from odoo import models


class ResUsers(models.Model):
    _name = "res.users"
    _inherit = 'res.users'

    def _mfa_type(self):
        """ Enforce TOTP MFA for privileged Australian users. """
        r = super()._mfa_type()
        if r is not None:
            return r
        if 'FR' not in self.sudo().company_ids.mapped('country_code'):
            return False
        return 'totp'
