from odoo import api, fields, models, _


class Bill(models.Model):
    _name = "pos.bill"
    _order = "value"
    _description = "Coins/Bills"

    name = fields.Char("Name")
    value = fields.Float("Coin/Bill Value", required=True, digits=0)
    pos_config_ids = fields.Many2many("pos.config")

    @api.model
    def name_create(self, name):
        result = super().create({"name": name, "value": float(name)})
        return result.name_get()[0]
