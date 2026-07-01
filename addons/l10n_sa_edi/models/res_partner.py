from odoo import fields, models, api
from odoo.exceptions import ValidationError
from odoo.addons.l10n_sa_edi.tools.partner_identifiers import SA_ADDITIONAL_IDENTIFIERS_METADATA


COMPANY_SCHEMES = {'CRN', 'MOM', 'MLS', '700', 'SAG', 'OTH'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sa_edi_building_number = fields.Char("Building Number")
    l10n_sa_edi_plot_identification = fields.Char("Secondary Number")

    l10n_sa_edi_additional_identification_scheme = fields.Char(
        compute='_compute_l10n_sa_edi_additional_identification_fields',
        inverse='_inverse_l10n_sa_edi_additional_identification_fields',
        string="Identification Scheme",
        help="Additional Identification Scheme for the Seller/Buyer",
    )

    l10n_sa_edi_additional_identification_number = fields.Char(
        string="Identification Number (SA)",
        compute='_compute_l10n_sa_edi_additional_identification_fields',
        inverse='_inverse_l10n_sa_edi_additional_identification_fields',
        help="Additional Identification Number for the Seller/Buyer",
    )

    _check_l10n_sa_edi_building_number = models.Constraint(
        "CHECK (l10n_sa_edi_building_number IS NULL OR l10n_sa_edi_building_number ~ '^[0-9]{4}$')",
        "Building Number must contain 4 numeric digits.",
        )
    _check_l10n_sa_edi_plot_number = models.Constraint(
        "CHECK (l10n_sa_edi_plot_identification IS NULL OR l10n_sa_edi_plot_identification ~ '^[0-9]{4}$')",
        "Secondary Number must contain 4 numeric digits.",
        )

    @api.depends('l10n_sa_edi_additional_identification_scheme', 'l10n_sa_edi_additional_identification_number')
    def _compute_is_company(self):
        """ Determines if a Saudi partner is a company or an individual based on VAT and
        additional identification fields.
        """
        l10n_sa_commercial_partners = self.filtered(
            lambda p: (
                p.country_code == 'SA'
                and p.commercial_partner_id == p
                and p._is_vat_void(p.vat)
                and p.l10n_sa_edi_additional_identification_number
                and p.l10n_sa_edi_additional_identification_scheme in COMPANY_SCHEMES
            )
        )
        l10n_sa_commercial_partners.is_company = True
        super(ResPartner, self - l10n_sa_commercial_partners)._compute_is_company()

    @api.depends('additional_identifiers')
    def _compute_l10n_sa_edi_additional_identification_fields(self):
        for partner in self:
            scheme = False
            number = False
            for identifier_type, identifier_value in (partner.additional_identifiers or {}).items():
                if identifier_type.startswith('SA_'):
                    scheme = identifier_type.removeprefix('SA_')
                    number = identifier_value
                    break
            partner.l10n_sa_edi_additional_identification_scheme = scheme
            partner.l10n_sa_edi_additional_identification_number = number

    def _inverse_l10n_sa_edi_additional_identification_fields(self):
        for partner in self:
            scheme = partner.l10n_sa_edi_additional_identification_scheme
            number = partner.l10n_sa_edi_additional_identification_number
            if scheme:
                partner._set_additional_identifier(f'SA_{scheme}', number or False)

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_sa_edi_building_number',
                                               'l10n_sa_edi_plot_identification',
                                               'l10n_sa_edi_additional_identification_scheme',
                                               'l10n_sa_edi_additional_identification_number']

    def _address_fields(self):
        return super()._address_fields() + ['l10n_sa_edi_building_number',
                                            'l10n_sa_edi_plot_identification']

    def _get_all_additional_identifiers_metadata(self):
        return {
            **super()._get_all_additional_identifiers_metadata(),
            **SA_ADDITIONAL_IDENTIFIERS_METADATA,
        }

    def _clean_additional_identifiers(self, vals):
        """Only one 'SA' additional identifier should be present in additional identifiers"""
        super()._clean_additional_identifiers(vals)

        identifiers = vals.get('additional_identifiers')
        if not identifiers:
            return vals

        sa_keys = [k for k in identifiers if k.startswith('SA_')]
        if len(sa_keys) > 1:
            raise ValidationError(self.env._("Only one Saudi Arabia identifier can be set at a time."))

        return vals
