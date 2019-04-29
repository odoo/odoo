# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResCompany(models.Model):

    _inherit = 'res.company'

    l10n_ar_identification_type_id = fields.Many2one(
        related='partner_id.l10n_ar_identification_type_id',
        readonly=False,
    )
    l10n_ar_id_number = fields.Char(
        related='partner_id.l10n_ar_id_number',
        readonly=False,
    )
    l10n_ar_cuit = fields.Char(
        related='partner_id.l10n_ar_cuit',
    )
    l10n_ar_country_code = fields.Char(
        related="country_id.code",
        string="Country code",
        help="Technical field use it in view attrs to show or not localization"
        " fields",
    )

    @api.multi
    def ensure_cuit(self):
        return self.partner_id.ensure_cuit()
