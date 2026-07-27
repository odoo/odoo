from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _check_bearer_credentials(cls, scope, token):
        if valid_credentials := super()._check_bearer_credentials(scope, token):
            return valid_credentials
        return request.env['oauth.access.token']._check_credentials(scope=scope, access_token=token)
