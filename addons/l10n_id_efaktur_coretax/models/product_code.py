# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class EfakturProductCode(models.Model):
    _name = "l10n_id_efaktur_coretax.product.code"
    _description = "Product categorization according to E-Faktur"

    code = fields.Char()
    description = fields.Text()

    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, f"{record.code} - {record.description}"))
        return result
