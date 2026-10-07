import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sa_edi_building_number = fields.Char("Building Number")
    l10n_sa_edi_plot_identification = fields.Char("Plot Identification")

    l10n_sa_additional_identification_scheme = fields.Selection([
        ('TIN', 'Tax Identification Number'),
        ('CRN', 'Commercial Registration Number'),
        ('MOM', 'Momra License'),
        ('MLS', 'MLSD License'),
        ('700', '700 Number'),
        ('SAG', 'Sagia License'),
        ('NAT', 'National ID'),
        ('GCC', 'GCC ID'),
        ('IQA', 'Iqama Number'),
        ('PAS', 'Passport ID'),
        ('OTH', 'Other ID')
    ], default="OTH", string="Identification Scheme", help="Additional Identification scheme for Seller/Buyer")

    l10n_sa_additional_identification_number = fields.Char("Identification Number (SA)",
                                                           help="Additional Identification Number for Seller/Buyer")

    l10n_sa_is_vat_group_member = fields.Boolean(
        compute='_compute_l10n_sa_is_vat_group_member'
    )

    @api.depends('vat', 'country_id')
    def _compute_l10n_sa_is_vat_group_member(self):
        for partner in self:
            # VAT group if 15-digit VAT with 11th digit = '1'
            vat = re.sub(r'\D', '', partner.vat or '')
            partner.l10n_sa_is_vat_group_member = (
                partner.country_id.code == 'SA'
                and len(vat) == 15
                and vat[10] == '1'
                and partner.ref_company_ids
            )

    @api.constrains('vat', 'l10n_sa_additional_identification_scheme', 'l10n_sa_additional_identification_number')
    def _check_l10n_sa_vat_group_tin(self):
        """
        Validate that VAT Group members have proper TIN configuration
        """
        # Skip validation during company creation to avoid errors with incomplete data
        if self.env.context.get('l10n_sa_skip_vat_group_validation'):
            return

        for partner in self:
            if not partner.l10n_sa_is_vat_group_member:
                continue
            errors = []
            if partner.l10n_sa_additional_identification_scheme != 'TIN':
                errors.append(_("Additional Identification Scheme as 'TIN'"))
            tin = re.sub(r'\D', '', partner.l10n_sa_additional_identification_number or '')
            if len(tin) != 10:
                errors.append(_("Additional Identification Number as the TIN Number(10 digits)"))
            if errors:
                raise ValidationError(_(
                    "To comply with ZATCA VAT Group onboarding rules, please set %s.",
                    " and ".join(errors)
                ))

    @api.onchange('vat', 'country_id')
    def _onchange_l10n_sa_vat_group_scheme(self):
        """Auto-set identification scheme to TIN for VAT Group members"""
        if self.l10n_sa_is_vat_group_member:
            self.l10n_sa_additional_identification_scheme = 'TIN'

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_sa_edi_building_number',
                                               'l10n_sa_edi_plot_identification',
                                               'l10n_sa_additional_identification_scheme',
                                               'l10n_sa_additional_identification_number']

    def _address_fields(self):
        return super()._address_fields() + ['l10n_sa_edi_building_number',
                                            'l10n_sa_edi_plot_identification']
