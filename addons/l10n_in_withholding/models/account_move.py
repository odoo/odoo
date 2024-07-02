from odoo import api, models, fields, _

from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_is_withholding = fields.Boolean(
        string="Is Indian TDS Entry",
        copy=False,
        help="Technical field to identify Indian withholding entry"
    )
    l10n_in_withholding_ref_move_id = fields.Many2one(
        comodel_name='account.move',
        string="Indian TDS Ref Move",
        readonly=True,
        copy=False,
        help="Reference move for withholding entry",
    )
    l10n_in_withholding_line_ids = fields.One2many('account.move.line', 'move_id',
        string="Indian TDS Lines",
        compute='_compute_l10n_in_withholding_line_ids',
    )
    l10n_in_total_withholding_amount = fields.Monetary(
        string="Total Indian TDS Amount",
        compute='_compute_l10n_in_total_withholding_amount',
        help="Total withholding amount for the move",
    )
    l10n_in_withhold_move_ids = fields.One2many('account.move', 'l10n_in_withholding_ref_move_id',
        string="Indian TDS Entries"
    )

    # === Compute Methods ===
    @api.depends('line_ids', 'l10n_in_is_withholding')
    def _compute_l10n_in_withholding_line_ids(self):
        # Compute the withholding lines for the move
        for move in self:
            if move.l10n_in_is_withholding:
                move.l10n_in_withholding_line_ids = move.line_ids.filtered('tax_ids')
            else:
                move.l10n_in_withholding_line_ids = False

    def _compute_l10n_in_total_withholding_amount(self):
        for move in self:
            move.l10n_in_total_withholding_amount = sum(move.l10n_in_withhold_move_ids.filtered(
                lambda m: m.state == 'posted').l10n_in_withholding_line_ids.mapped('l10n_in_withhold_tax_amount'))

    def js_assign_outstanding_line(self, line_id):
        # Override this method to restrict the withholding entry to be assigned to another move
        self.ensure_one()
        line = self.env['account.move.line'].browse(line_id)
        if line.move_id.l10n_in_is_withholding:
            if self.partner_id == line.move_id.l10n_in_withholding_ref_move_id.payment_id.partner_id:
                # If the withholding entry is already assigned to the same partner's payment, then reconcile it
                return super().js_assign_outstanding_line(line_id)
            elif line.move_id.l10n_in_withholding_ref_move_id != self:
                wh_move = line.move_id.l10n_in_withholding_ref_move_id
                raise ValidationError(_("This withholding entry is already assigned to %s (%s) and cannot be reassigned to another record.", wh_move.type_name, wh_move.name))
        return super().js_assign_outstanding_line(line_id)

    def action_l10n_in_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "TDS Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.l10n_in_withhold_move_ids.ids)],
        }
