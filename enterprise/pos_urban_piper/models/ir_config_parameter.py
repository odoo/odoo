from odoo import models, _
from odoo.exceptions import ValidationError


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def write(self, vals):
        for rec in self:
            if rec.key == 'pos_urban_piper.uuid' and (vals.get('key') or vals.get('value')):
                raise ValidationError(
                    _("You cannot change the pos_urban_piper.uuid.")
                )
        return super().write(vals)
