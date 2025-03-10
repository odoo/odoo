# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    extra_hours_leave_type_id = fields.Many2one('hr.leave.type')
