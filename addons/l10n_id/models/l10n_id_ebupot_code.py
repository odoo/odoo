# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class L10n_IdEbupotCode(models.Model):
    _name = 'l10n_id.ebupot.code'
    _description = "E-Bupot Object Code"

    code = fields.Char(string="Code", required=True)
    name = fields.Char(string="Name", required=True)

    _code_uniq = models.Constraint('unique (code)', 'The Object Code must be unique.')

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for ebupot_code in self:
            ebupot_code.display_name = f"{ebupot_code.code} - {ebupot_code.name}"
