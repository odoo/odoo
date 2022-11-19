from odoo import api, fields, models


class Bill(models.Model):
    _name = "pos.bill"
    _order = "value"
    _description = "Coins/Bills"

    name = fields.Char("Name")
    value = fields.Float("Coin/Bill Value", required=True)
    pos_config_ids = fields.Many2many("pos.config", string="Point of Sales")

    @api.model
    def name_create(self, name):
        result = super().create({"name": name, "value": float(name)})
        return result.name_get()[0]

    @api.onchange('value')
    def onchange_value(self):
        self.name = self.value