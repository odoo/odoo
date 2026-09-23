from odoo import models
from odoo.exceptions import AccessError
from odoo.tools.misc import str2bool


class ResUsersApikeys(models.Model):
    _inherit = "res.users.apikeys"

    def _check_generate_access(self):
        try:
            return super()._check_generate_access()
        except AccessError:
            allow_portal = str2bool(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("portal.allow_api_keys"),
                default=False,
            )
            if not allow_portal:
                raise
            if self.env.user._is_portal():
                return None
            raise AccessError(
                self.env._("Only internal and portal users can create API keys")
            ) from None
