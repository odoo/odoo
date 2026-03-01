from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPkEdiSroItem(models.Model):
    _name = "l10n_pk_edi.sro.item"
    _description = "Pakistan Statutory Regulatory Order Item"

    name = fields.Char()
    sro_id = fields.Many2one("l10n_pk_edi.sro", string="Statutory Regulatory Order Schedule")

    @api.constrains('name', 'sro_id')
    def _constraint_sro_item_name(self):
        for record in self:
            if record.sro_id and record.name in record.sro_id.sro_item_ids.filtered(lambda r: r != record).mapped('name'):
                raise UserError(_("Statutory Regulatory Order item names must be unique within the same Statutory Regulatory Order Schedule."))
