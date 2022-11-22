from odoo import fields, models, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_sa_edi_building_number = fields.Char("Building Number")
    l10n_sa_edi_plot_identification = fields.Char("Plot Identification")
    l10n_sa_edi_neighborhood = fields.Char("Neighborhood")

    l10n_sa_additional_identification_scheme = fields.Selection([
        ('CRN', 'Commercial Registration Number'),
        ('MOM', 'Momra License'),
        ('MLS', 'MLSD License'),
        ('SAG', 'Sagia License'),
        ('OTH', 'Other OD')
    ], default="CRN", string="Identification Scheme", help="Seller Identification scheme")

    l10n_sa_additional_identification_number = fields.Char("Identification Number", copy=False, help="Seller Identification Number")

    def _display_address_depends(self):
        return super(ResPartner, self)._display_address_depends() + ['l10n_sa_edi_building_number',
                                                                     'l10n_sa_edi_plot_identification',
                                                                     'l10n_sa_edi_neighborhood']

    @api.model
    def _get_default_address_format(self):
        return "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(l10n_sa_edi_building_number)s %(l10n_sa_edi_plot_identification)s\n%(l10n_sa_edi_neighborhood)s\n%(country_name)s"
