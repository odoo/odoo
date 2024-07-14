# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    is_quantity = fields.Boolean(related='deduction_type_id.is_quantity')
    is_refund = fields.Boolean()

    def _get_active_amount(self):
        return sum(a.active_amount * (-1 if a.is_refund else 1) for a in self)
