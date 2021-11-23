from werkzeug.exceptions import BadRequest, Unauthorized

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_calendar_ics(cls):
        key = request.get_http_params().get('key')
        if not key:
            raise BadRequest()

        uid = request.env['res.users.apikeys']._check_credentials(scope='calendar.ics', key=key)
        if not uid:
            raise Unauthorized()

        request.update_env(user=uid)
