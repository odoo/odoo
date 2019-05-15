# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import re


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ar_cuit = fields.Char(
        compute='_compute_l10n_ar_cuit',
        string="CUIT",
        help='Computed field that returns cuit or nothing if this one is not'
        ' set for the partner',
    )
    l10n_ar_formated_cuit = fields.Char(
        compute='_compute_l10n_ar_formated_cuit',
        string="Formated CUIT",
        help='Computed field that will convert the given cuit number to the'
        ' format {person_category:2}-{number:10}-{validation_number:1}',
    )
    l10n_ar_identification_type_id = fields.Many2one(
        string="Identification Type",
        comodel_name='l10n_ar.identification.type',
        index=True,
        auto_join=True,
        help='The type od identifications defined by AFIP that could identify'
        ' a person or a legal entity when trying to made operations',
    )

    @api.multi
    def ensure_cuit(self):
        """ This method is a helper that returns the cuit number is this one is
        defined if not raise an UserError.

        CUIT is not mandatory field but for some Argentinian operations the
        cuit is required, for eg  validate an electronic invoice, build a
        report, etc.

        This method can be used to validate is the cuit is proper defined in
        the partner
        """
        self.ensure_one()
        if not self.l10n_ar_cuit:
            raise UserError(_(
                'No CUIT configured for partner [%i] %s') % (
                    self.id, self.name))
        return self.l10n_ar_cuit

    @api.depends('l10n_ar_cuit')
    def _compute_l10n_ar_formated_cuit(self):
        """ This will add some dash to the CUIT number in order to show in his
        natural format: {person_category}-{number}-{validation_number}
        """
        for rec in self:
            if not rec.l10n_ar_cuit:
                continue
            cuit = rec.l10n_ar_cuit
            rec.l10n_ar_formated_cuit = "{0}-{1}-{2}".format(
                cuit[0:2], cuit[2:10], cuit[10:])

    @api.depends('l10n_ar_identification_type_id', 'vat')
    def _compute_l10n_ar_cuit(self):
        """ We add this computed field that returns cuit or nothing ig this one
        is not set for the partner. This validation can be also done by calling
        ensure_cuit() method that returns the cuit or error if this one is not
        found.
        """
        for rec in self:
            if rec.l10n_ar_identification_type_id.afip_code == 80:
                rec.l10n_ar_cuit = rec.vat
            # If the partner is outside Argentina then we return the defined
            # country cuit defined by AFIP for that specific partner
            elif rec.country_id and country.code != 'AR':
                rec.l10n_ar_cuit = rec.commercial_partner_id.is_company and \
                    rec.country_id.l10n_ar_cuit_juridica or \
                    rec.country_id.l10n_ar_cuit_fisica
