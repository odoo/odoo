# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'


    l10n_latam_identification_type_id = fields.Many2one('l10n_latam.identification.type',
            string="Identification Type", index=True, auto_join=True,
            domain="['|', ('country_id', '=', country_id), ('is_foreign', '=', True)]",
            help="The type of identifications defined for LATAM countries")

    l10n_latam_identification_type_required = fields.Boolean('Identification Type required', compute="_compute_identification_type_required")

    @api.depends('country_id')
    def _compute_identification_type_required(self):
        for partner in self:
            partner.l10n_latam_identification_type_required = bool(self.env['l10n_latam.identification.type'].search([('country_id', '=', partner.country_id.id)], limit=1))

    @api.onchange('country_id')
    def _onchange_country(self):
        # If latam american country, then take identification type of type VAT by default
        idtype = self.env['l10n_latam.identification.type'].search([('country_id', '=', self.country_id.id),
                                                                    ('is_vat', '=', True)], limit=1)
        self.l10n_latam_identification_type_id = idtype and idtype.id or False