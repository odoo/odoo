from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_pl_mpp = fields.Boolean(
        string='MPP',
        related='move_id.l10n_pl_mpp',
    )
