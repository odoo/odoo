from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Bill(models.Model):
    _name = "pos.bill"
    _order = "value"
    _description = "Coins/Bills"

    name = fields.Char("Name")
    value = fields.Float("Coin/Bill Value", required=True, digits=0)
    pos_config_ids = fields.Many2many("pos.config", string="Point of Sales")

    @api.model
    def _name_create_values(self, name):
        vals = super()._name_create_values(name)
        try:
            vals['value'] = float(name)
        except:
            raise UserError(_("The name of the Coins/Bills must be a number."))
        return vals
