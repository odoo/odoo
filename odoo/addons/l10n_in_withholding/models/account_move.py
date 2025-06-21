from odoo import api, models, fields


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
    l10n_in_withhold_move_ids = fields.One2many(
        'account.move', 'l10n_in_withholding_ref_move_id',
        string="Indian TDS Entries"
    )
    l10n_in_withholding_line_ids = fields.One2many(
        'account.move.line', 'move_id',
        string="Indian TDS Lines",
        compute='_compute_l10n_in_withholding_line_ids',
    )
    l10n_in_total_withholding_amount = fields.Monetary(
        string="Total Indian TDS Amount",
        compute='_compute_l10n_in_total_withholding_amount',
        help="Total withholding amount for the move",
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

    def action_l10n_in_withholding_entries(self):
        self.ensure_one()
        return {
            'name': "TDS Entries",
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.l10n_in_withhold_move_ids.ids)],
        }
