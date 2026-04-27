
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    expense_extract_show_ocr_option_selection = fields.Selection(related='company_id.expense_extract_show_ocr_option_selection',
        string='Expense processing option', readonly=False)
