# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductCombo(models.Model):
    _name = 'product.combo'
    _description = "Product Combo"
    _order = 'sequence, id'

    name = fields.Char(string="Name", required=True)
    sequence = fields.Integer(default=10, copy=False)
    combo_item_ids = fields.One2many(
        comodel_name='product.combo.item',
        inverse_name='combo_id',
        copy=True,
    )
    combo_item_count = fields.Integer(string="Product Count", compute='_compute_combo_item_count')
    base_price = fields.Float(
        string="Combo Price",
        help="The minimum price among the products in this combo. This value will be used to"
             " prorate the price of this combo with respect to the other combos in a combo product."
             " This ensures that whatever product the user chooses in a combo, it will always be"
             " the same price.",
        compute='_compute_base_price',
    )

    @api.depends('combo_item_ids')
    def _compute_combo_item_count(self):
        # Initialize combo_item_count to 0 as _read_group won't return any results for new combos.
        self.combo_item_count = 0
        # Optimization to count the number of combo items in each combo.
        for combo, item_count in self.env['product.combo.item']._read_group(
            domain=[('combo_id', 'in', self.ids)],
            groupby=['combo_id'],
            aggregates=['__count'],
        ):
            combo.combo_item_count = item_count

    @api.depends('combo_item_ids')
    def _compute_base_price(self):
        for combo in self:
            combo.base_price = min(
                combo.combo_item_ids.mapped('lst_price')
            ) if combo.combo_item_ids else 0

    @api.constrains('combo_item_ids')
    def _check_combo_item_ids_not_empty(self):
        if any(not combo.combo_item_ids for combo in self):
            raise ValidationError(_("A combo must have at least 1 combo item."))
