import time

from odoo import models

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    def create(self, vals):
        delay = self.env['ir.config_parameter'].sudo().get_param('hr_expense_debug.expense_create_delay', False)
        if delay:
            time.sleep(int(delay))
        return super().create(vals)
