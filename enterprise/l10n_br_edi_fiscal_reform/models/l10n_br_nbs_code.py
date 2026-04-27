# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class L10NBSCode(models.Model):
    _name = 'l10n_br.nbs.code'
    _description = 'NBS Code'
    _rec_names_search = ['code', 'name']

    code = fields.Char('Code', required=True)
    name = fields.Char('Name', required=True)

    _sql_constraints = [('code_uniq', 'unique (code)', 'The code must be unique.')]

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}"
