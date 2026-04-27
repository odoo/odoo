# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def l10n_be_soda_open_soda_mapping(self):
        wizard = self.env['soda.import.wizard'].create({
            'soda_files': {},
            'company_id': self.env.company.id,
        })
        return {
            'name': _('SODA Mapping'),
            'view_id': self.env.ref('l10n_be_soda.soda_import_wizard_view_form').id,
            'res_model': 'soda.import.wizard',
            'res_id': wizard.id,
            'context': {**self.env.context, 'soda_mapping_save_only': True},
            'type': 'ir.actions.act_window',
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'new',
        }
