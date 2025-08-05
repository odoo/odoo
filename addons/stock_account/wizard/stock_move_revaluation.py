from odoo import api, fields, models


class StockMoveRevaluation(models.TransientModel):
    _name = 'stock.move.revaluation'
    _description = 'Stock Move Revaluation'

    move_id = fields.Many2one('stock.move', string='Stock Move', required=True)
    currency = fields.Many2one('res.currency', string='Currency', related='move_id.company_id.currency_id')
    current_value = fields.Monetary('Current Value', related="move_id.value", currency_field='currency')
    new_value = fields.Monetary('New Value', required=True, currency_field='currency')
    description = fields.Char('Description')

    @api.model_create_multi
    def create(self, vals_list):
        revaluations = super().create(vals_list)
        for revaluation in revaluations:
            move = revaluation.move_id
            self.env['product.value'].create({
                'move_id': move.id,
                'value': revaluation.new_value,
                'company_id': revaluation.move_id.company_id.id,
                'description': revaluation.description,
            })
        revaluations.move_id._set_value()
        return revaluations
