# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'IN':
            fields += ['l10n_in_hsn_code']
        return fields

    @api.onchange('l10n_in_hsn_code')
    def _onchange_l10n_in_hsn_code(self):
        if self._origin.l10n_in_hsn_code and self.env['pos.session'].search_count([('state', '!=', 'closed')]):
            raise UserError(_("Unable to change the HSN/SAC code. Please ensure all POS sessions are closed before proceeding."))
