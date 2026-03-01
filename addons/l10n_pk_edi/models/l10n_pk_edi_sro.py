from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.l10n_pk_edi.data.l10n_pk_edi_data import TRANSACTION_TYPE


class L10nPkEdiSro(models.Model):
    _name = "l10n_pk_edi.sro"
    _description = "Pakistan FBR SRO"

    name = fields.Char()
    sro_item_ids = fields.One2many("l10n_pk_edi.sro.item", 'sro_id')
    l10n_pk_edi_transaction_type = fields.Selection(
        selection=TRANSACTION_TYPE,
        string="Transaction Type",
        required=True,
    )

    @api.constrains('name', 'l10n_pk_edi_transaction_type')
    def _constraint_sro_name(self):
        for record in self:
            # Check for duplicates across same transaction type
            duplicate_sros = self.search([('l10n_pk_edi_transaction_type', '=', record.l10n_pk_edi_transaction_type), ('id', '!=', record.id)])
            for sro in duplicate_sros:
                if sro.name == record.name:
                    raise UserError(_("SRO with the same name already exist for this transaction type."))
