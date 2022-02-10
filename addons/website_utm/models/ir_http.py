# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _serve_fallback(cls):
        resp = super()._serve_fallback()
        if resp:
            cls._set_utm()
        return resp
