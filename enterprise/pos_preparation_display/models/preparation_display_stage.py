from odoo import fields, models


class PosPreparationStage(models.Model):
    _name = 'pos_preparation_display.stage'
    _description = "Point of Sale preparation stage"
    _order = 'sequence, id'

    name = fields.Char("Name", required=True)
    color = fields.Char("Color")
    alert_timer = fields.Integer(string="Alert timer (min)", help="Timer after which the order will be highlighted")
    preparation_display_id = fields.Many2one('pos_preparation_display.display', string="Preparation display", ondelete='cascade')
    sequence = fields.Integer('Sequence')
