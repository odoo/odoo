from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    l10n_in_hsn_code = fields.Char(string="HSN/SAC Code", compute="_compute_l10n_in_hsn_code", store=True, readonly=False, copy=False)

    @api.depends('product_id', 'product_id.l10n_in_hsn_code')
    def _compute_l10n_in_hsn_code(self):
        for line in self:
            if line.move_id.country_code == 'IN' and line.parent_state == 'draft':
                line.l10n_in_hsn_code = line.product_id.l10n_in_hsn_code

    def write(self, vals):
        fields_to_check = {
            'tax_tag_ids': 'Tax Grids',
            'l10n_in_hsn_code': 'HSN/SAC Code',
            'product_uom_id': 'Unit Of Measure'
        }
        posted_lines = self.filtered(lambda line: line.parent_state == 'posted')
        for field in fields_to_check:
            if field in vals and any(line[field] for line in posted_lines):
                raise UserError(_('You cannot modify the %s related to a posted journal item. Reset the journal entry to draft to do so.', fields_to_check[field]))
        return super().write(vals)
