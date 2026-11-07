# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
import stdnum.ar
import re
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):

    _inherit = 'res.partner'

    l10n_ar_vat = fields.Char(
        compute='_compute_l10n_ar_vat', string="VAT", help='Computed field that returns VAT or nothing if this one'
        ' is not set for the partner')
    l10n_ar_formatted_vat = fields.Char(
        compute='_compute_l10n_ar_formatted_vat', string="Formatted VAT", help='Computed field that will convert the'
        ' given VAT number to the format {person_category:2}-{number:10}-{validation_number:1}')

    l10n_ar_gross_income_number = fields.Char('Gross Income Number')
    l10n_ar_gross_income_type = fields.Selection(
        [('multilateral', 'Multilateral'), ('local', 'Local'), ('exempt', 'Exempt')],
        'Gross Income Type', help='Argentina: Type of gross income: exempt, local, multilateral.')
    l10n_ar_afip_responsibility_type_id = fields.Many2one(
        'l10n_ar.afip.responsibility.type', string='AFIP Responsibility Type', index='btree_not_null', help='Defined by AFIP to'
        ' identify the type of responsibilities that a person or a legal entity could have and that impacts in the'
        ' type of operations and requirements they need.')
    l10n_ar_special_purchase_document_type_ids = fields.Many2many(
        'l10n_latam.document.type', 'res_partner_document_type_rel', 'partner_id', 'document_type_id',
        string='Other Purchase Documents', help='This field will be deprecated in the next version as it is no longer needed.')

    @api.depends('l10n_ar_vat')
    def _compute_l10n_ar_formatted_vat(self):
        """ This will add some dash to the CUIT number (VAT AR) in order to show in his natural format:
        {person_category}-{number}-{validation_number} """
        recs_ar_vat = self.filtered('l10n_ar_vat')
        for rec in recs_ar_vat:
            try:
                rec.l10n_ar_formatted_vat = stdnum.ar.cuit.format(rec.l10n_ar_vat)
            except Exception as error:
                rec.l10n_ar_formatted_vat = rec.l10n_ar_vat
                _logger.runbot("Argentinean VAT was not formatted: %s", repr(error))
        remaining = self - recs_ar_vat
        remaining.l10n_ar_formatted_vat = False

    @api.depends('vat', 'l10n_latam_identification_type_id')
    def _compute_l10n_ar_vat(self):
        """ We add this computed field that returns cuit (VAT AR) or nothing if this one is not set for the partner.
        This Validation can be also done by calling ensure_vat() method that returns the cuit (VAT AR) or error if this
        one is not found """
        recs_ar_vat = self.filtered(lambda x: x.l10n_latam_identification_type_id.l10n_ar_afip_code == '80' and x.vat)
        for rec in recs_ar_vat:
            rec.l10n_ar_vat = stdnum.ar.cuit.compact(rec.vat)
        remaining = self - recs_ar_vat
        remaining.l10n_ar_vat = False

    @api.constrains('vat', 'l10n_latam_identification_type_id')
    def check_vat(self):
        """ Since we validate more documents than the vat for Argentinean partners (CUIT - VAT AR, CUIL, DNI) we
        extend this method in order to process it. """
        # NOTE by the moment we include the CUIT (VAT AR) validation also here because we extend the messages
        # errors to be more friendly to the user. In a future when Odoo improve the base_vat message errors
        # we can change this method and use the base_vat.check_vat_ar method.s
        l10n_ar_partners = self.filtered(lambda p: p.l10n_latam_identification_type_id.l10n_ar_afip_code or p.country_code == 'AR')
        l10n_ar_partners.l10n_ar_identification_validation()
        return super(ResPartner, self - l10n_ar_partners).check_vat()

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_ar_afip_responsibility_type_id']

    def ensure_vat(self):
        """ This method is a helper that returns the VAT number is this one is defined if not raise an UserError.

        VAT is not mandatory field but for some Argentinean operations the VAT is required, for eg  validate an
        electronic invoice, build a report, etc.

        This method can be used to validate is the VAT is proper defined in the partner """
        self.ensure_one()
        if not self.l10n_ar_vat:
            raise UserError(_('No VAT configured for partner [%i] %s', self.id, self.name))
        return self.l10n_ar_vat

    def _get_validation_module(self):
        self.ensure_one()
        if self.l10n_latam_identification_type_id.l10n_ar_afip_code in ['80', '86']:
            return stdnum.ar.cuit
        elif self.l10n_latam_identification_type_id.l10n_ar_afip_code == '96':
            return stdnum.ar.dni

    def l10n_ar_identification_validation(self):
        for rec in self.filtered('vat'):
            try:
                module = rec._get_validation_module()
            except Exception as error:
                module = False
                _logger.runbot("Argentinean document was not validated: %s", repr(error))

            if not module:
                continue
            try:
                module.validate(rec.vat)
            except module.InvalidChecksum:
                raise ValidationError(_('The validation digit is not valid for "%s"',
                                        rec.l10n_latam_identification_type_id.name))
            except module.InvalidLength:
                raise ValidationError(_('Invalid length for "%s"', rec.l10n_latam_identification_type_id.name))
            except module.InvalidFormat:
                raise ValidationError(_('Only numbers allowed for "%s"', rec.l10n_latam_identification_type_id.name))
            except Exception as error:
                raise ValidationError(repr(error))

    def _get_id_number_sanitize(self):
        """ Sanitize the identification number. Return the digits/integer value of the identification number
        If not vat number defined return 0 """
        self.ensure_one()
        if not self.vat:
            return 0
        if self.l10n_latam_identification_type_id.l10n_ar_afip_code in ['80', '86']:
            # Compact is the number clean up, remove all separators leave only digits
            res = int(stdnum.ar.cuit.compact(self.vat))
        else:
            id_number = re.sub('[^0-9]', '', self.vat)
            res = int(id_number)
        return res
