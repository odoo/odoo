from odoo import fields, models, api


class PosComboLine(models.Model):
    _name = "pos.combo.line"
    _description = "Product Combo Items"
    _inherit = ['pos.load.mixin']

    product_id = fields.Many2one("product.product", string="Product", required=True)
    combo_price = fields.Float("Price Extra", default=0.0)
    lst_price = fields.Float("Original Price", related="product_id.lst_price")
    combo_id = fields.Many2one("pos.combo")

    @api.model
    def _load_pos_data_domain(self, data):
        return [('id', 'in', list(set().union(*[combo.get('combo_line_ids') for combo in data['pos.combo']['data']])))]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'product_id', 'combo_price', 'combo_id']
