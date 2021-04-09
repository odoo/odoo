from odoo import fields, models
# from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rejected_check_account_id = fields.Many2one(
        related='company_id.rejected_check_account_id',
        readonly=False,
    )
    deferred_check_account_id = fields.Many2one(
        related='company_id.deferred_check_account_id',
        readonly=False,
    )
    holding_check_account_id = fields.Many2one(
        related='company_id.holding_check_account_id',
        readonly=False,
    )
