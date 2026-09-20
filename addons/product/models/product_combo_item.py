from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductComboItem(models.Model):
    _name = "product.combo.item"
    _description = "Product Combo Item"
    _check_company_auto = True

    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Options",
        required=True,
        domain=[("type", "!=", "combo")],
        ondelete="restrict",
        check_company=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="product_id.currency_id",
    )
    lst_price = fields.Float(
        related="product_id.lst_price",
        string="Original Price",
        min_display_digits="Product Price",
    )
    combo_id = fields.Many2one(
        comodel_name="product.combo",
        index=True,
        required=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="combo_id.company_id",
    )
    extra_price = fields.Float(
        min_display_digits="Product Price",
        default=0.0,
    )

    @api.constrains("product_id")
    def _check_product_id_no_combo(self):
        if any(combo_item.product_id.type == "combo" for combo_item in self):
            raise ValidationError(
                _('A combo choice can\'t contain products of type "combo".')
            )

    def unlink(self):
        combo_ids = set(self.combo_id.ids)
        res = super().unlink()
        if combo_ids:
            self.env.cr.precommit.data.setdefault(
                "product.combo.emptied", set()
            ).update(combo_ids)
            self.env.cr.precommit.add(self._check_combos_not_emptied)
        return res

    @api.model
    def _check_combos_not_emptied(self):
        combo_ids = self.env.cr.precommit.data.pop("product.combo.emptied", ())
        combos = self.env["product.combo"].browse(combo_ids).exists()
        if not combos:
            return
        remaining = dict(
            self._read_group(
                [("combo_id", "in", combos.ids)], ["combo_id"], ["__count"]
            )
        )
        emptied = combos.filtered(lambda combo: not remaining.get(combo))
        if emptied:
            raise ValidationError(
                _(
                    "A combo must keep at least 1 choice: %(combos)s would be left"
                    " empty. Delete the combo itself instead.",
                    combos=", ".join(emptied.mapped("name")),
                )
            )
