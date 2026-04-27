from odoo import fields, models


class PosPreparationDisplayOrderStage(models.Model):
    _name = 'pos_preparation_display.order.stage'
    _description = "Stage of orders by preparation display"

    stage_id = fields.Many2one('pos_preparation_display.stage', ondelete='cascade')
    preparation_display_id = fields.Many2one("pos_preparation_display.display", index=True, ondelete='cascade')
    order_id = fields.Many2one('pos_preparation_display.order', index=True, ondelete='cascade')
    done = fields.Boolean("Is the order done")
