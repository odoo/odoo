from odoo import models, _
from odoo.exceptions import AccessError


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    def write(self, vals):
        if not self.env.su and self.env.user._is_portal():
            raise AccessError(_("Sequences can not be modified by portal users."))
        return super().write(vals)
