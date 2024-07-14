from odoo import models, fields

class ModelAction(models.Model):
    _name = "test.studio.model_action"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Test Model Studio"

    name = fields.Char()
    confirmed = fields.Boolean()
    step = fields.Integer()

    def action_confirm(self):
        for rec in self:
            rec.confirmed = True

    def action_step(self):
        for rec in self:
            rec.step = rec.step + 1

class ModelAction2(models.Model):
    _inherit = "test.studio.model_action"
    _name = "test.studio.model_action2"
    _description = "Test Model Studio 2"
