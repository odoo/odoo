from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_sa_edi_building_number = fields.Char(string="Building Number")
    l10n_sa_edi_plot_identification = fields.Char(string="Plot Identification")

    l10n_sa_edi_additional_identification_scheme = fields.Selection(
        selection=[
            ("TIN", "Tax Identification Number"),
            ("CRN", "Commercial Registration Number"),
            ("MOM", "Momra License"),
            ("MLS", "MLSD License"),
            ("700", "700 Number"),
            ("SAG", "Sagia License"),
            ("NAT", "National ID"),
            ("GCC", "GCC ID"),
            ("IQA", "Iqama Number"),
            ("PAS", "Passport ID"),
            ("OTH", "Other ID"),
        ],
        string="Identification Scheme",
        default="OTH",
        help="Additional Identification Scheme for the Seller/Buyer",
    )

    l10n_sa_edi_additional_identification_number = fields.Char(
        string="Identification Number (SA)",
        help="Additional Identification Number for the Seller/Buyer",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "l10n_sa_edi_building_number",
            "l10n_sa_edi_plot_identification",
            "l10n_sa_edi_additional_identification_scheme",
            "l10n_sa_edi_additional_identification_number",
        ]

    def _address_fields(self):
        return super()._address_fields() + [
            "l10n_sa_edi_building_number",
            "l10n_sa_edi_plot_identification",
        ]
