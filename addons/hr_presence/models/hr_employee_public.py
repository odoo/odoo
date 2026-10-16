# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    email_sent = fields.Boolean(default=False)
    ip_connected = fields.Boolean(default=False)
