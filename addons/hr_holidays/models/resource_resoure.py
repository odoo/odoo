# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    leave_date_to = fields.Date(related="user_id.leave_date_to")
