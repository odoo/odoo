# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.onchange('l10n_in_hsn_code')
    def _onchange_l10n_in_hsn_code(self):
        if self._origin.l10n_in_hsn_code and self.env['pos.session'].search_count([('state', '!=', 'closed')]):
            raise UserError(_("Unable to change the HSN/SAC code. Please ensure all POS sessions are closed before proceeding."))
