from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = "stock.move"

    l10n_mx_edi_is_hazardous_material = fields.Boolean(
        string="Is Hazardous Material",
        compute='_compute_l10n_mx_edi_is_hazardous_material',
    )

    @api.depends('product_id')
    def _compute_l10n_mx_edi_is_hazardous_material(self):
        for move in self:
            move.l10n_mx_edi_is_hazardous_material = \
                move.product_id.unspsc_code_id.l10n_mx_edi_hazardous_material and \
                move.product_id.l10n_mx_edi_hazardous_material_code_id
