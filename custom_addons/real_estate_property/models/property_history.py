from odoo import fields,models,api
from odoo.exceptions import ValidationError


class PropertyHistory(models.Model):
    _name = "property.history"
    _description = "Property History"

    user_id = fields.Many2one('res.users', string='User')
    property_id = fields.Many2one('property', string='Property')
    old_state = fields.Char()
    new_state = fields.Char()
    reason = fields.Char()
    line_ids = fields.One2many('property.history.line', 'history_id', string='History Lines')



class PropertyHistoryLine(models.Model):
    _name = "property.history.line"
    _description = "Property History Line"

    area = fields.Float()
    description = fields.Char()
    history_id = fields.Many2one('property.history', string='history')

