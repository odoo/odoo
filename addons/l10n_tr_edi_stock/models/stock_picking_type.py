from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'
    l10n_tr_nilvera_gib_sequence_code = fields.Char('GIB Sequence Prefix', compute="_compute_l10n_tr_nilvera_gib_sequence_code")

    @api.model
    def _get_gib_sequence_prefix_from_sequence_code(self, sequence_code):
        """Return the 3-char GIB prefix parsed from the sequence code for NILVERA.

        Rules:
        - Prefix must be exactly 3 alphanumeric characters.
        - A single trailing non-alphanumeric character is allowed and ignored.
        """
        if not sequence_code or len(sequence_code) < 3:
            return False

        if sequence_code[-1].isalnum():
            gib_prefix = sequence_code[-3:]
        else:
            if len(sequence_code) < 4:
                return False
            gib_prefix = sequence_code[-4:-1]

        return gib_prefix if gib_prefix.isalnum() else False

    @api.depends('sequence_code', 'company_id.account_fiscal_country_id.code', 'code')
    def _compute_l10n_tr_nilvera_gib_sequence_code(self):
        for picking_type in self:
            is_tr = (picking_type.company_id.account_fiscal_country_id.code == 'TR')
            is_outgoing = (picking_type.code == 'outgoing')
            picking_type.l10n_tr_nilvera_gib_sequence_code = (
                picking_type._get_gib_sequence_prefix_from_sequence_code(picking_type.sequence_code)
                if is_tr and is_outgoing
                else False
            )

    @api.onchange('sequence_code')
    def _onchange_sequence_code(self):
        gib_prefix = self._get_gib_sequence_prefix_from_sequence_code(self.sequence_code)
        if (
            self.company_id.account_fiscal_country_id.code == 'TR'
            and self.code == 'outgoing'
            and self.sequence_code
            and not gib_prefix
        ):
            raise UserError(_("Odoo extracts the last 3 letters of the Sequence Prefix as the GIB prefix for e-Dispatch orders."
                              "\n\nValid examples:"
                              "\nOUT/"
                              "\nOUT-"
                              "\nWH/OUT"
                              "\nWH-OUT"
                              "\nWH/OUT/"
                              "\n\nPlease update the Sequence Code so the last 3 characters form a valid prefix."))
        return super()._onchange_sequence_code()

    def _get_action(self, action_xmlid):
        action = super()._get_action(action_xmlid)
        action['context']['restricted_picking_type_code'] = self.code
        return action
