from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def _get_debug_modes(self):
        return super()._get_debug_modes() | {'translate'}
