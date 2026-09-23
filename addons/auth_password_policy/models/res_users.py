from odoo import api, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    @api.model
    def get_password_policy(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "minlength": int(
                params.get_param("auth_password_policy.minlength", default=0)
            ),
        }

    def _inverse_password(self):
        self._check_password_policy(self.mapped("password"))

        super()._inverse_password()

    def _check_password_policy(self, passwords):
        failures = []
        params = self.env["ir.config_parameter"].sudo()

        minlength = int(params.get_param("auth_password_policy.minlength", default=0))
        for password in passwords:
            if not password:
                continue
            if len(password) < minlength:
                failures.append(
                    self.env._(
                        "Your password must contain at least %(minimal_length)d characters and only has %(current_count)d.",
                        minimal_length=minlength,
                        current_count=len(password),
                    )
                )

        if failures:
            raise UserError("\n\n ".join(failures))
