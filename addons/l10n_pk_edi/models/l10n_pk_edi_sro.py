from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import SALE_TYPE


class L10nPkEdiSro(models.Model):
    _name = "l10n_pk_edi.sro"
    _description = "Pakistan Statutory Regulatory Order"

    name = fields.Char(string="Statutory Regulatory Order Schedule")
    sro_item_ids = fields.One2many("l10n_pk_edi.sro.item", 'sro_id', string="Statutory Regulatory Order Items")
    l10n_pk_edi_sale_type = fields.Selection(selection=SALE_TYPE, string="Sale Type", required=True)

    @api.constrains('name', 'l10n_pk_edi_sale_type')
    def _constraint_sro_name(self):
        for record in self:
            # Check for duplicates across same Sale type
            duplicate_sros = self.search([('l10n_pk_edi_sale_type', '=', record.l10n_pk_edi_sale_type), ('id', '!=', record.id)])
            for sro in duplicate_sros:
                if sro.name == record.name:
                    raise UserError(_("Statutory Regulatory Order with the same name already exist for this Sale type."))
