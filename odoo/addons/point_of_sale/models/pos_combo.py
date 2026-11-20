from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PosCombo(models.Model):
    """
    This model is used to allow the pos user to create menus.
    This means that products can be grouped together and sold as a combo.

    ex: Create a product called `Burger Menu`
        - This product will have multiple combos associated with it, for ex:
            - Drinks - will contain the list of drinks from which the customer can choose
            - Main Course - will contain the list of main courses from which the customer can choose
            - Dessert - will contain the list of desserts from which the customer can choose
        The `Burger Menu` will have a certain price, for example 20$ and the rest of the
        products will be listed with a price of 0$.
        In the event that one of the products inside one of the combos is to be more expensive,
        this product will have a specific `combo_price` which will be added to the total price
    """
    _name = "pos.combo"
    _description = "Product combo choices"
    _order = "sequence, id"
    name = fields.Char(string="Name", required=True)
    combo_line_ids = fields.One2many("pos.combo.line", "combo_id", string="Products in Combo", copy=True)
    num_of_products = fields.Integer("No of Products", compute="_compute_num_of_products")
    sequence = fields.Integer(copy=False)
    base_price = fields.Float(
        compute="_compute_base_price",
        string="Product Price",
        help="The value from which pro-rating of the component price is based. This is to ensure that whatever product the user chooses for a component, it will always be they same price."
    )

    @api.depends("combo_line_ids")
    def _compute_num_of_products(self):
        """
        the read_group only returns info for the combos that have at least one line.
        This is normally fine, because all the combos will have at least one line.
        The problem is that this function is also run when the user creates a new combo,
        and at that point, the combo doesn't have any lines, so the read_group will return
        nothing and the function will fail to set the value of `num_of_products` to 0, thus
        resulting in an error.
        """
        for rec in self:
            rec.num_of_products = 0
        # optimization trick to count the number of products in each combo
        for combo, num_of_products in self.env["pos.combo.line"]._read_group([("combo_id", "in", self.ids)], groupby=["combo_id"], aggregates=["__count"]):
            combo.num_of_products = num_of_products

    @api.constrains("combo_line_ids")
    def _check_combo_line_ids_is_not_null(self):
        if any(not rec.combo_line_ids for rec in self):
            raise ValidationError(_("Please add products in combo."))

    @api.depends("combo_line_ids")
    def _compute_base_price(self):
        for rec in self:
            # Use the lowest price of the combo lines as the base price
            rec.base_price = min(rec.combo_line_ids.mapped("product_id.lst_price")) if rec.combo_line_ids else 0
