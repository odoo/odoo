import re

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

CABYS_RE = re.compile(r'^\d{13}$')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_cr_fe_cabys = fields.Char(string="Código CABYS")
    l10n_cr_fe_cabys_descripcion = fields.Char(string="Descripción CABYS", readonly=True)

    @api.constrains('l10n_cr_fe_cabys')
    def _check_l10n_cr_fe_cabys(self):
        for product in self:
            if product.l10n_cr_fe_cabys and not CABYS_RE.match(product.l10n_cr_fe_cabys):
                raise ValidationError(
                    _("El código CABYS de '%s' debe tener exactamente 13 dígitos.") % product.name)

    def action_l10n_cr_fe_buscar_cabys(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_cr.fe.cabys.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_product_id': self.id},
        }
