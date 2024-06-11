from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import check_barcode_encoding


class AcRoleType(models.Model):
    _name = 'l10n_es_edi_facturae_adm_centers.ac_role_type'
    _description = 'Administrative Center Role Type'

    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)


class Partner(models.Model):
    _inherit = 'res.partner'

    type = fields.Selection(selection_add=[('facturae_ac', 'FACe Center'), ('other',)])
    l10n_es_edi_facturae_ac_center_code = fields.Char(string='Code', size=10, help="Code of the issuing department.")
    l10n_es_edi_facturae_ac_role_type_ids = fields.Many2many(
        string='Roles',
        comodel_name='l10n_es_edi_facturae_adm_centers.ac_role_type',
        help="It indicates the role played by the Operational Point defined as a Workplace/Department.\n"
             "These functions are:\n"
             "- Receiver: Workplace associated to the recipient's tax identification number where the invoice will be received.\n"
             "- Payer: Workplace associated to the recipient's tax identification number responsible for paying the invoice.\n"
             "- Buyer: Workplace associated to the recipient's tax identification number who issued the purchase order.\n"
             "- Collector: Workplace associated to  the issuer's tax identification number responsible for handling the collection.\n"
             "- Fiscal: Workplace associated to the recipient's tax identification number, where an Operational Point mailbox is shared "
             "by different client companies with different tax identification numbers and it is necessary to differentiate between "
             "where the message is received (shared letterbox) and the workplace where it must be stored (recipient company).",
    )
    l10n_es_edi_facturae_ac_physical_gln = fields.Char(
        string='Physical GLN',
        size=14,
        help="Identification of the connection point to the VAN EDI (Global Location Number). Barcode of 13 standard positions. "
        "Codes are registered in Spain by AECOC. The code is made up of the country code (2 positions) Spain is '84' "
        "+ Company code (5 positions) + the remaining positions. The last one is the product + check digit."
    )
    l10n_es_edi_facturae_ac_logical_operational_point = fields.Char(
        string='Logical Operational Point',
        size=14,
        help="Code identifying the company. Barcode of 13 standard positions. Codes are registered in Spain by AECOC. "
        "The code is made up of the country code (2 positions) Spain is '84' + Company code (5 positions) + the remaining positions. "
        "The last one is the product + check digit.",
    )

    @api.constrains('l10n_es_edi_facturae_ac_physical_gln')
    def _validate_l10n_es_edi_facturae_ac_physical_gln(self):
        for p in self:
            if not p.l10n_es_edi_facturae_ac_physical_gln:
                continue
            if not check_barcode_encoding(p.l10n_es_edi_facturae_ac_physical_gln, 'ean13'):
                raise ValidationError(_('The Physical GLN entered is not valid.'))

    @api.constrains('l10n_es_edi_facturae_ac_logical_operational_point')
    def _validate_l10n_es_edi_facturae_ac_logical_operational_point(self):
        for p in self:
            if not p.l10n_es_edi_facturae_ac_logical_operational_point:
                continue
            if not check_barcode_encoding(p.l10n_es_edi_facturae_ac_logical_operational_point, 'ean13'):
                raise ValidationError(_('The Logical Operational Point entered is not valid.'))
