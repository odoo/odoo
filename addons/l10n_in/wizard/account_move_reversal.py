from odoo import api, models, fields


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    l10n_in_adjustment_type = fields.Selection(
        [
            ('standard', 'Standard'),
            ('price_adjustment', 'Price Adjustment'),
        ],
        string="Adjustment Type",
        default='standard',
    )

    l10n_in_show_adjustment_type = fields.Boolean(compute='_compute_l10n_in_show_adjustment_type')

    @api.depends('move_ids')
    def _compute_l10n_in_show_adjustment_type(self):
        for record in self:
            record.l10n_in_show_adjustment_type = (
                record.country_code == 'IN'
                and all(move.move_type == 'out_invoice' for move in record.move_ids)
            )

    def _prepare_default_reversal(self, move):
        res = super()._prepare_default_reversal(move)
        if move.country_code == 'IN' and move.move_type == 'out_invoice':
            res['l10n_in_adjustment_type'] = self.l10n_in_adjustment_type
        return res
