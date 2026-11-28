from odoo import api, fields, models


class L10n_Tr_EdiAliasWizard(models.TransientModel):
    _inherit = 'l10n_tr_edi.alias.wizard'

    alias_type = fields.Selection(
        selection_add=[('edispatch', "e-Dispatch")],
        ondelete={'edispatch': 'cascade'},
    )

    @api.model
    def _get_partner_alias_field(self, alias_type):
        # EXTENDS 'l10n_tr_edi'
        if alias_type == 'edispatch':
            return 'l10n_tr_edi_edispatch_alias'
        return super()._get_partner_alias_field(alias_type)
