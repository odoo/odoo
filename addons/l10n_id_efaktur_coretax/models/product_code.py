# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class EfakturProductCode(models.Model):
    _name = "l10n_id_efaktur_coretax.product.code"
    _description = "Product categorization according to E-Faktur"

    code = fields.Char()
    description = fields.Text()

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.description}"
