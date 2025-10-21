# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class ProductCombo(models.Model):
    _name = 'product.combo'
    _inherit = ['product.combo', 'pos.load.mixin']

    qty_max = fields.Integer(string="Maximum quantity", default=1, help="Maximum number of items to select in the combo.")
    qty_free = fields.Integer(string="Free quantity", default=1, help="Number of free items included in the combo.")
    is_upsell = fields.Boolean(string="Is Upsell", default=False, help="Indicates if the combo is an upsell to the customer. This can be compared to a minimum quantity of 0.")

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', list(set().union(*[product.get('combo_ids') for product in data['product.template']])))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'combo_item_ids', 'base_price', 'qty_free', 'qty_max', 'is_upsell', 'sequence']

    @api.onchange('is_upsell')
    def _onchange_is_upsell(self):
        if self.is_upsell:
            self.qty_free = 0
        if not self.is_upsell and self.qty_free == 0:
            self.qty_free = 1

    @api.constrains('qty_max')
    def _check_qty_max(self):
        if any(combo.qty_max < 1 for combo in self):
            raise ValidationError(_("The maximum quantity of a combo must be greater or equal to 1."))

    @api.constrains('qty_free')
    def _check_qty_free(self):
        if any(combo.qty_free < 1 and not combo.is_upsell for combo in self):
            raise ValidationError(_("The free quantity of a combo must be greater or equal to 1."))
        if any(combo.is_upsell and combo.qty_free != 0 for combo in self):
            raise ValidationError(_("The free quantity of an upsell combo must be equal to 0."))

    @api.constrains('qty_max', 'qty_free')
    def _check_qty_max_greater_than_qty_free(self):
        if any(combo.qty_free > combo.qty_max for combo in self):
            raise ValidationError(_("The free quantity must be smaller or equal to the maximum quantity."))
