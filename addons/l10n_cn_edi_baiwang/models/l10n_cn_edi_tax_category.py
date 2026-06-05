# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api

class L10nCnEdiTaxCategory(models.Model):
    _name = 'l10n_cn_edi.tax.category'
    _description = 'China Tax Category Code'
    _rec_names_search = ['name', 'code']  # Allows searching the dropdown by either name or code
    
    name = fields.Char(string="Category Name", required=True)
    code = fields.Char(string="Tax Classification Code", required=True)
    active = fields.Boolean(default=True)

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            if record.code and record.name:
                record.display_name = f"{record.code} {record.name}"
            else:
                record.display_name = record.name or record.code
