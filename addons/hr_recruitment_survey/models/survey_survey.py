# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Survey(models.Model):
    _inherit = 'survey.survey'

    category = fields.Selection(selection_add=[('hr_recruitment', 'Recruitment')])
