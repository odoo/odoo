from odoo import fields, models


class ResPartnerIdentification(models.Model):
    _inherit = 'res.partner.identification'

    is_ubl_cii = fields.Boolean(compute='_compute_is_ubl_cii')

    # Computed "quick access" fields
    def _compute_is_ubl_cii(self):
        for identification in self:
            identification.is_ubl_cii = self._get_code_vals(identification.code).get('ubl_cii', False)
