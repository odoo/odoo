from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_fr_is_valid_sea_grant = fields.Boolean(compute='_compute_is_valid_sea_grant')

    @api.depends('invoice_line_ids.product_id', 'partner_id', 'state')
    def _compute_is_valid_sea_grant(self):
        for move in self:
            if move.partner_id.country_code == 'FR' and move.state == 'posted':
                move.l10n_fr_is_valid_sea_grant = (
                    all(line.product_id.l10n_fr_border_reference for line in move.invoice_line_ids)
                )
            else:
                move.l10n_fr_is_valid_sea_grant = True
