# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
        string="Identification Type", index=True, auto_join=True,
        domain=lambda self: "['|', ('country_id', '=', False), ('country_id', '=', country_id or %s)]" % (
            self.env.user.company_id.country_id.id),
        help="The type of identifications defined for LATAM countries")
    vat = fields.Char(string='VAT/Identification Number')

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_latam_identification_type_id']
