##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################
from odoo import models, fields, api


class ResCompany(models.Model):

    _inherit = 'res.company'

    l10n_ar_id_category_id = fields.Many2one(
        related='partner_id.l10n_ar_id_category_id',
    )
    l10n_ar_id_number = fields.Char(
        related='partner_id.l10n_ar_id_number',
    )
    l10n_ar_cuit = fields.Char(
        related='partner_id.l10n_ar_cuit'
    )

    @api.multi
    def cuit_required(self):
        return self.partner_id.cuit_required()
