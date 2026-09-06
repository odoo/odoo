# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EfakturProductCode(models.Model):
    _name = "l10n_id_efaktur_coretax.product.code"
    _description = "Product categorization according to E-Faktur"
    _rec_name = "code"
    _rec_names_search = ['code', 'description']

    code = fields.Char()
    description = fields.Text()

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.description}"

    def _search_display_name(self, operator, value):
        # Try to reverse the `name_get` structure
        parts = value.split(' - ')
        if len(parts) == 2:
            return [('code', operator, parts[0]), ('description', operator, parts[1])]
        return super()._search_display_name(operator, value)
