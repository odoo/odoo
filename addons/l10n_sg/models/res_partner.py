from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sg_unique_entity_number = fields.Char(
        string='UEN',
        compute='_compute_l10n_sg_unique_entity_number',
        inverse='_inverse_l10n_sg_unique_entity_number',
    )

    @api.depends('additional_identifiers')
    def _compute_l10n_sg_unique_entity_number(self):
        for partner in self:
            partner.l10n_sg_unique_entity_number = partner._get_additional_identifier('SG_UEN')

    def _inverse_l10n_sg_unique_entity_number(self):
        for partner in self:
            partner._set_additional_identifier('SG_UEN', partner.l10n_sg_unique_entity_number)

    def _deduce_country_code(self):
        self.ensure_one()
        if self._get_additional_identifier('SG_UEN'):
            return 'SG'
        return super()._deduce_country_code()
