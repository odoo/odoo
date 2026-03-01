from odoo import _, api, fields, models
from odoo.exceptions import UserError


class L10nPkEdiSroItem(models.Model):
    _name = "l10n_pk_edi.sro.item"
    _description = "Pakistan FBR SRO Item"

    name = fields.Char()
    sro_id = fields.Many2one("l10n_pk_edi.sro")

    @api.constrains('name', 'sro_id')
    def _constraint_sro_item_name(self):
        for record in self:
            if record.sro_id and record.name in record.sro_id.sro_item_ids.filtered(lambda r: r != record).mapped('name'):
                raise UserError(_("SRO item names must be unique within the same SRO Schedule."))
