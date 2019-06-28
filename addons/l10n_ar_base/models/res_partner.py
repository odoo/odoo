# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import stdnum.ar


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ar_cuit = fields.Char(
        compute='_compute_l10n_ar_cuit', string="CUIT", help='Computed field that returns cuit or nothing if this one'
        ' is not set for the partner')
    l10n_ar_formated_cuit = fields.Char(
        compute='_compute_l10n_ar_formated_cuit', string="Formated CUIT", help='Computed field that will convert the'
        ' given cuit number to the format {person_category:2}-{number:10}-{validation_number:1}')

    @api.multi
    def ensure_cuit(self):
        """ This method is a helper that returns the cuit number is this one is defined if not raise an UserError.

        CUIT is not mandatory field but for some Argentinian operations the cuit is required, for eg  validate an
        electronic invoice, build a report, etc.

        This method can be used to validate is the cuit is proper defined in the partner """
        self.ensure_one()
        if not self.l10n_ar_cuit:
            raise UserError(_('No CUIT configured for partner [%i] %s') % (self.id, self.name))
        return self.l10n_ar_cuit

    @api.depends('l10n_ar_cuit')
    def _compute_l10n_ar_formated_cuit(self):
        """ This will add some dash to the CUIT number in order to show in his natural format:
        {person_category}-{number}-{validation_number} """
        for rec in self.filtered('l10n_ar_cuit'):
            rec.l10n_ar_formated_cuit = stdnum.ar.cuit.format(rec.l10n_ar_cuit)

    @api.depends('vat', 'l10n_latam_identification_type_id')
    def _compute_l10n_ar_cuit(self):
        """ We add this computed field that returns cuit or nothing ig this one is not set for the partner. This
        Validation can be also done by calling ensure_cuit() method that returns the cuit or error if this one is not
        found."""
        for rec in self:
            commercial_partner = rec.commercial_partner_id
            if rec.l10n_latam_identification_type_id.l10n_ar_afip_code == 80:
                rec.l10n_ar_cuit = rec.vat
            # If the partner is outside Argentina then we return the defined
            # country cuit defined by AFIP for that specific partner
            elif commercial_partner.country_id and commercial_partner.country_id != self.env.ref('base.ar'):
                rec.l10n_ar_cuit = commercial_partner.country_id[
                    commercial_partner.is_company and 'l10n_ar_cuit_juridica' or 'l10n_ar_cuit_fisica']

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def check_vat(self):
        l10n_ar_partners = self.filtered('l10n_latam_identification_type_id')
        l10n_ar_partners.l10n_ar_identification_validation()
        return super(ResPartner, self - l10n_ar_partners).check_vat()

    def _get_validation_module(self):
        self.ensure_one()
        if self.l10n_latam_identification_type_id.l10n_ar_afip_code in [80, 86]:
            return stdnum.ar.cuit
        elif self.l10n_latam_identification_type_id.l10n_ar_afip_code == 96:
            return stdnum.ar.dni

    def l10n_ar_identification_validation(self):
        for rec in self.filtered('vat'):
            module = rec._get_validation_module()
            if not module:
                continue
            try:
                module.validate(rec.vat)
            except module.InvalidChecksum:
                raise ValidationError(_('The validation digit is not valid.'))
            except module.InvalidLength:
                raise ValidationError(_('Invalid length.'))
            except module.InvalidFormat:
                raise ValidationError(_('Only numbers allowed.'))
            except Exception as error:
                raise ValidationError(repr(error))
