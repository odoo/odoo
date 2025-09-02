from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sg_unique_entity_number = fields.Char(string='UEN', compute='_compute_l10n_sg_unique_entity_number')

    @api.depends('identifier_ids')
    def _compute_l10n_sg_unique_entity_number(self):
        for partner in self:
            partner.l10n_sg_unique_entity_number = partner.identifier_ids.filtered(lambda i: i.code == 'SG:UEN').identifier
