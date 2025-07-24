from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import check_barcode_encoding


class L10n_Es_Edi_FacturaeAc_Role_Type(models.Model):
    _name = 'l10n_es_edi_facturae.ac_role_type'
    _description = 'Administrative Center Role Type'

    code = fields.Char(required=True)
    name = fields.Char(required=True, translate=True)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    invoice_edi_format = fields.Selection(selection_add=[('es_facturae', 'Spain (FacturaE)')])
    type = fields.Selection(selection_add=[('facturae_ac', 'FACe Center'), ('other',)])
    l10n_es_edi_facturae_ac_center_code = fields.Char(string='Code', size=10, help="Code of the issuing department.")
    l10n_es_edi_facturae_ac_role_type_ids = fields.Many2many(
        string='Roles',
        comodel_name='l10n_es_edi_facturae.ac_role_type',
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
    l10n_es_edi_facturae_residence_type = fields.Char(string='Facturae EDI Residency Type Code',
        compute='_compute_l10n_es_edi_facturae_residence_type', store=False, readonly=True,)

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

    @api.depends('country_id')
    def _compute_l10n_es_edi_facturae_residence_type(self):
        eu_country_ids = self.env.ref('base.europe').country_ids.ids
        for partner in self:
            country = partner.country_id
            if country.code == 'ES':
                partner.l10n_es_edi_facturae_residence_type = 'R'
            elif country.id in eu_country_ids:
                partner.l10n_es_edi_facturae_residence_type = 'U'
            else:
                partner.l10n_es_edi_facturae_residence_type = 'E'

    def _l10n_es_edi_facturae_export_check(self):
        errors = {}
        if invalid_records := self.filtered(lambda partner: not (partner.is_company or partner.vat)):
            errors["l10n_es_edi_facturae_partner_check"] = {
                'level': 'danger',
                'message': _("Partner must be a company or have a VAT number"),
                'action_text': _("View Partner(s)"),
                'action': invalid_records._get_records_action(name=_("Check Partner(s)")),
            }
        return errors
