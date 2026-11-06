from odoo import fields, models

class AdmissionStage(models.Model):
    _name = 'admission.stage'
    _description = 'Admission Pipeline Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    is_won = fields.Boolean(string='Is Won Stage')
    fold = fields.Boolean(string='Folded in Kanban')