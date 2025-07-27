# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrHolidaysCancelLeave(models.TransientModel):
    _inherit = 'hr.holidays.cancel.leave'
    _description = 'Cancel Time Off Wizard'

    before_linked_sandwich_leave_id = fields.Many2one(related='leave_id.before_linked_sandwich_leave_id')
    after_linked_sandwich_leave_id = fields.Many2one(related='leave_id.after_linked_sandwich_leave_id')
