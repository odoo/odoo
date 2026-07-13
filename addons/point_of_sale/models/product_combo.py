# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class ProductCombo(models.Model):
    _name = 'product.combo'
    _inherit = ['product.combo', 'pos.load.mixin']

    qty_max = fields.Integer(string="Maximum quantity", default=1, help="Maximum number of items to select in the combo.")
    is_upsell = fields.Boolean(string="Is Upsell", default=False, help="Indicates if the combo is an upsell to the customer. This can be compared to a minimum quantity of 0.")
    upsell_warning = fields.Char(compute="_compute_upsell_warning")

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', list(set().union(*[product.get('combo_ids') for product in data['product.template']])))]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'combo_item_ids', 'base_price', 'qty_free', 'qty_max', 'is_upsell', 'sequence', 'currency_id']

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)
        self._convert_pos_data_currency(read_records, config, 'base_price', 'currency_id')
        return read_records

    @api.depends('is_upsell')
    def _compute_upsell_warning(self):
        for record in self:
            record.upsell_warning = _(
                "⚠️ This item is configured as Upsell. "
                "Go to Point of Sale to disable Upsell if you want to modify 'Included'."
            ) if record.is_upsell else False

    @api.onchange('is_upsell')
    def _onchange_is_upsell(self):
        for record in self:
            if record.is_upsell:
                record.qty_free = 0

    @api.constrains('qty_max')
    def _check_qty_max(self):
        if any(combo.qty_max < 1 for combo in self):
            raise ValidationError(_("The maximum quantity of a combo must be greater or equal to 1."))

    @api.constrains('qty_free', 'is_upsell')
    def _check_qty_free(self):
        upsell_combos = self.filtered(lambda combo: combo.is_upsell)
        if any(combo.qty_free != 0 for combo in upsell_combos):
            raise ValidationError(_("The free quantity of an upsell combo must be equal to 0."))
        super(ProductCombo, self - upsell_combos)._check_qty_free()

    @api.onchange('qty_max', 'qty_free')
    def _onchange_qty_free_adjust_qty_max(self):
        for combo in self:
            if combo.qty_free > combo.qty_max:
                combo.qty_max = combo.qty_free
