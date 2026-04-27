from odoo import fields, models
from .l10n_pe_edi_vehicle import ISSUING_ENTITY

class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_pe_edi_operator_license = fields.Char(
        string="Driver's License",
        help="This person's driver's license number, for generating the Delivery Guide.",
    )
    l10n_pe_edi_mtc_number = fields.Char(
        string="MTC Registration Number",
        help="Peru: Ministry of Transport and Communication Registration Number."
    )
    l10n_pe_edi_authorization_issuing_entity = fields.Selection(
        selection=ISSUING_ENTITY,
        string="Authorization Issuing Entity",
        help="Peru: Entity issuing the special authorization for the transportation of the goods."
    )
    l10n_pe_edi_authorization_number = fields.Char(
        string="Authorization Number",
        help="Peru: Authorization number for the transportation of the goods.",
    )
