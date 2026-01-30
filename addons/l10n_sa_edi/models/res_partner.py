from odoo import fields, models, api

COMPANY_SCHEMES = {'CRN', 'MOM', 'MLS', '700', 'SAG', 'OTH'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sa_edi_building_number = fields.Char("Building Number")
    l10n_sa_edi_plot_identification = fields.Char("Plot Identification")

    l10n_sa_edi_additional_identification_scheme = fields.Selection([
        ('TIN', 'Tax Identification Number'),
        ('CRN', 'Commercial Registration Number'),
        ('MOM', 'MOMRAH License'),
        ('MLS', 'MHRSD License'),
        ('700', '700 Number'),
        ('SAG', 'MISA License'),
        ('NAT', 'National ID'),
        ('GCC', 'GCC ID'),
        ('IQA', 'Iqama Number'),
        ('PAS', 'Passport ID'),
        ('OTH', 'Other ID')
    ], default="OTH", string="Identification Scheme", help="Additional Identification Scheme for the Seller/Buyer")

    l10n_sa_edi_additional_identification_number = fields.Char("Identification Number (SA)", help="Additional Identification Number for the Seller/Buyer")

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

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['l10n_sa_edi_building_number',
                                               'l10n_sa_edi_plot_identification',
                                               'l10n_sa_edi_additional_identification_scheme',
                                               'l10n_sa_edi_additional_identification_number']

    def _address_fields(self):
        return super()._address_fields() + ['l10n_sa_edi_building_number',
                                            'l10n_sa_edi_plot_identification']
