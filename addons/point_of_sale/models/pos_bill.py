from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosBill(models.Model):
    _name = 'pos.bill'
    _order = "value"
    _description = "Coin/Bill"
    _inherit = ["pos.load.mixin"]

    name = fields.Char("Name", required=True)
    value = fields.Float("Value", required=True, digits=(16, 4))
    pos_config_ids = fields.Many2many("pos.config", string="Point of Sales")

    @api.constrains('value')
    def _check_value_not_zero(self):
        for bill in self:
            if bill.value <= 0:
                raise ValidationError(_("The value of a coin/bill must be greater than 0."))

    @api.model
    def _load_pos_data_domain(self, data, config):
        return ['|', ('id', 'in', config.default_bill_ids.ids), ('pos_config_ids', '=', False)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'value']
