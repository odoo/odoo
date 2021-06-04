# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = "res.company"

    refuse_existing_applications = fields.Boolean("Close Other Applications On Hire", default=True)
