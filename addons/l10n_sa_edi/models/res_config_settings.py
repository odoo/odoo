from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_sa_production_env = fields.Boolean(related='company_id.l10n_sa_production_env', readonly=False)

    @api.depends('company_id')
    def _compute_company_informations(self):
        super()._compute_company_informations()
        for record in self:
            record.company_informations += _('\nBuilding Number: %s, Plot Identification: %s \nNeighborhood: %s') % (self.company_id.l10n_sa_edi_building_number, self.company_id.l10n_sa_edi_plot_identification, self.company_id.l10n_sa_edi_neighborhood)
