from odoo import models, fields


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_in_fiscal_position_type = fields.Selection(
        selection=[
            ("inter_state", "Inter State"),
            ("intra_state", "Intra State"),
        ],
        string="Indian Fiscal Position Type",
    )
