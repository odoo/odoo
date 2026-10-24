from odoo import models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    def write(self, vals):
        if vals.get('password'):
            self._l10n_pt_check_password_set_by_self()
        return super().write(vals)

    def _l10n_pt_check_password_set_by_self(self):
        """
        Nobody but the user may know the password of a user of a Portuguese company, the
        administrator included (Despacho 8632/2014 3.1.1): such a user chooses it, from an invitation
        or a password reset. The superuser, i.e. scripts and the user's own password change, is not
        concerned. A user created with a password (an import, a test) is not either: the interface
        invites new users to choose theirs.
        """
        if self.env.su:
            return
        if others := self.filtered(lambda u: (
            u != self.env.user
            and u.company_ids.filtered(lambda c: c.account_fiscal_country_id.code == 'PT')
        )):
            raise UserError(self.env._(
                "You cannot set the password of %(users)s: users of a Portuguese company choose their own "
                "password, which nobody else may know. Use \"Send Password Reset Instructions\" instead.",
                users=", ".join(others.mapped('name')),
            ))
