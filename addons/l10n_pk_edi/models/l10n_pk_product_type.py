# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class L10nPkProductType(models.Model):
    _name = "l10n.pk.product.type"
    _description = 'Product Sale Type'
    _rec_name = 'display_name'

    name = fields.Char('Sale Type', required=True)
    sale_type = fields.Char('Sale Type Code', required=True)

    @api.depends('name', 'sale_type')
    def _compute_display_name(self):
        for line in self:
            line.display_name = f"[{line.sale_type}] {line.name}"
