from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import OR


class PosBill(models.Model):
    _name = 'pos.bill'
    _order = "value"
    _description = "Coins/Bills"
    _inherit = ["pos.load.mixin"]

    name = fields.Char("Name")
    value = fields.Float("Value", required=True, digits=(16, 4))
    pos_config_ids = fields.Many2many("pos.config", string="Point of Sales")

    @api.model
    def name_create(self, name):
        try:
            value = float(name)
        except ValueError:
            raise UserError(_("The name of the Coins/Bills must be a number."))
        result = super().create({"name": name, "value": value})
        return result.id, result.display_name

    @api.model
    def _load_pos_data_domain(self, data):
        return ['|', ('id', 'in', data['pos.config'][0]['default_bill_ids']), ('pos_config_ids', '=', False)]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'value']
