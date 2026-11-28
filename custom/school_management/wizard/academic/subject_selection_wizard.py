from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SubjectSelectionWizard(models.TransientModel):
    _name = 'subject.selection.wizard'
    _description = 'Subject Selection Wizard'

    curriculum_id = fields.Many2one('university.curriculum', string='Curriculum')
