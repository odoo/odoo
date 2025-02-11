from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_create_delay = fields.Integer(
        config_parameter="hr_expense_debug.expense_create_delay",
        help="Additional delay when creating an expense.",
    )
