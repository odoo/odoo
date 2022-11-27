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
        try:
            value = float(name)
            result = super().create({"name": name, "value": value})
            return result.name_get()[0]
        except: # will not be raised, but just so that it makes sense
            raise UserWarning("user is recommended to input name aligned with the value")

    @api.constrains('value')
    def _onchange_value(self):
        if self.value <= 0:
            raise UserWarning("user must input a positive value")
        else:
            self.name = self.value
