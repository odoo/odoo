from odoo import models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _load_pos_data_fields(self, config):
        return [
            *super()._load_pos_data_fields(config),
            'l10n_sa_edi_building_number',
            'l10n_sa_edi_plot_identification',
            'l10n_sa_edi_additional_identification_scheme',
            'l10n_sa_edi_additional_identification_number',
        ]
