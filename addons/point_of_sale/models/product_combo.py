# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class ProductCombo(models.Model):
    _name = 'product.combo'
    _inherit = ['product.combo', 'pos.load.mixin']

    qty_max = fields.Integer(string="Maximum quantity", default=1, help="Maximum number of items to select in the combo.")
    included_qty = fields.Integer(string="Included", default=1, help="Number of free items included in the combo.")
    is_upsell = fields.Boolean(string="Is Upsell", default=False, help="Indicates if the combo is an upsell to the customer. This can be compared to a minimum quantity of 0.")

    @api.model
    def _load_pos_data_domain(self, data):
        combo_ids = data['product.template'].combo_ids.ids
        return [('id', 'in', combo_ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.combo.item']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'combo_item_ids', 'base_price', 'included_qty', 'qty_max', 'is_upsell', 'sequence', 'currency_id']

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        self._convert_pos_data_currency(read_records, config, 'base_price', 'currency_id')
        return read_records

    @api.onchange('is_upsell')
    def _onchange_is_upsell(self):
        if self.is_upsell:
            self.included_qty = 0
        if not self.is_upsell and self.included_qty == 0:
            self.included_qty = 1

    @api.constrains('qty_max')
    def _check_qty_max(self):
        if any(combo.qty_max < 1 for combo in self):
            raise ValidationError(_("The maximum quantity of a combo must be greater or equal to 1."))

    @api.constrains('included_qty')
    def _check_included_qty(self):
        if any(combo.included_qty < 1 and not combo.is_upsell for combo in self):
            raise ValidationError(_("The included quantity of a combo must be greater or equal to 1."))
        if any(combo.is_upsell and combo.included_qty != 0 for combo in self):
            raise ValidationError(_("The included quantity of an upsell combo must be equal to 0."))

    @api.constrains('qty_max', 'included_qty')
    def _check_qty_max_greater_than_included_qty(self):
        if any(combo.included_qty > combo.qty_max for combo in self):
            raise ValidationError(_("The included quantity must be smaller or equal to the maximum quantity."))
