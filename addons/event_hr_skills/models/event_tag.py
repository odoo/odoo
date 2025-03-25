# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventTagCategory(models.Model):
    _inherit = 'event.tag.category'

    resume_line_type_id = fields.Many2one('hr.resume.line.type', "Type of corresponding resume lines")
