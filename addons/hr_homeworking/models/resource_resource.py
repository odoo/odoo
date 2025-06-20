# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResourceResource(models.Model):
    _inherit = "resource.resource"

    remote_work_location_type = fields.Char(related="employee_id.remote_work_location_type")
