# coding: utf-8

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # == Address ==
    l10n_mx_edi_locality = fields.Char(
        string="Locality Name",
        store=True, readonly=False,
        compute='_compute_l10n_mx_edi_locality')
    l10n_mx_edi_locality_id = fields.Many2one(
        comodel_name='l10n_mx_edi.res.locality',
        string="Locality",
        help="Optional attribute used in the XML that serves to define the locality where the domicile is located.")
    l10n_mx_edi_colony = fields.Char(
        string="Colony Name")
    l10n_mx_edi_colony_code = fields.Char(
        string="Colony Code",
        help="Note: Only use this field if this partner is the company address or if it is a branch office.\n"
             "Colony code that will be used in the CFDI with the external trade as Emitter colony. It must be a code "
             "from the SAT catalog.")

    # == External Trade ==
    l10n_mx_edi_curp = fields.Char(
        string="CURP", size=18,
        help="In Mexico, the Single Code of Population Registration (CURP) is a unique alphanumeric code of 18 "
             "characters used to officially identify both residents and Mexican citizens throughout the country.")
    l10n_mx_edi_external_trade = fields.Boolean(
        'Need external trade?', help='check this box to add by default '
        'the external trade complement in invoices for this customer.')
    l10n_mx_edi_external_trade_type = fields.Selection(
        selection=[
            ('02', 'Definitive'),
            ('03', 'Temporary'),
        ],
        string='External Trade',
        help="Mexico: Indicates whether the partner is foreign and if an External Trade complement is required."
             "01 - Not Set: No Complement."
             "02 - Definitive: Adds the External Trade complement to CFDI."
             "03 - Temporal: Used when exporting goods for a temporary period.",
    )

    @api.depends('l10n_mx_edi_locality_id')
    def _compute_l10n_mx_edi_locality(self):
        for partner in self:
            partner.l10n_mx_edi_locality = partner.l10n_mx_edi_locality_id.name

    @api.model
    def _formatting_address_fields(self):
        """Returns the list of address fields usable to format addresses."""
        return super(ResPartner, self)._formatting_address_fields() + ['l10n_mx_edi_colony',
                                                                       'l10n_mx_edi_locality', 'l10n_mx_edi_colony_code']
