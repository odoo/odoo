# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class ProductCombo(models.Model):
    _name = 'product.combo'
    _inherit = ['product.combo', 'pos.load.mixin']

    qty_max = fields.Integer(string="Maximum quantity", default=1, help="Maximum number of items to select in the combo.")
    qty_free = fields.Integer(string="Free quantity", default=1, help="Number of free items included in the combo.")

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', list(set().union(*[product.get('combo_ids') for product in data['product.template']])))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'combo_item_ids', 'base_price', 'qty_free', 'qty_max']

    @api.constrains('qty_max')
    def _check_qty_max(self):
        if any(combo.qty_max < 1 for combo in self):
            raise ValidationError(_("The maximum quantity of a combo must be greater or equal to 1."))

    @api.constrains('qty_free')
    def _check_qty_free(self):
        if any(combo.qty_free < 0 for combo in self):
            raise ValidationError(_("The free quantity of a combo must be greater or equal to 0."))

    @api.constrains('qty_max', 'qty_free')
    def _check_qty_max_greater_than_qty_free(self):
        if any(combo.qty_free > combo.qty_max for combo in self):
            raise ValidationError(_("The free quantity must be smaller or equal to the maximum quantity."))
