from odoo import models
from odoo.exceptions import AccessDenied


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _auth_method_thing(cls):
        raise AccessDenied()
