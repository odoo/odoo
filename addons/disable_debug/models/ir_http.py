from odoo import models
from odoo.http import request
from ..shared.user import (
    can_enter_debug_mode
)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _handle_debug(cls):
        if 'debug' in request.httprequest.args:
            if can_enter_debug_mode(request.env.user):
                return super(IrHttp, cls)._handle_debug()
            request.session.debug = ''
