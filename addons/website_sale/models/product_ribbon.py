from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductRibbon(models.Model):
    _name = "product.ribbon"
    _description = "Product ribbon"
    _order = "sequence ASC, id"

    name = fields.Char(
        string="Ribbon Name",
        size=20,
        translate=True,
        required=True,
    )
    sequence = fields.Integer(default=10)
    bg_color = fields.Char(
        string="Background Color",
        default="#000000",
        required=True,
    )
    text_color = fields.Char(
        default="#FFFFFF",
        required=True,
    )
    position = fields.Selection(
        selection=[("left", "Left"), ("right", "Right")],
        default="left",
        required=True,
    )
    style = fields.Selection(
        selection=[("ribbon", "Ribbon"), ("tag", "Badge")],
        default="ribbon",
        required=True,
        help="Defines the display style:\n"
        "- Ribbon: Shows a ribbon banner on the product image.\n"
        "- Badge: Shows a small badge label on the product image.",
    )
    assign = fields.Selection(
        selection=[
            ("manual", "Manually"),
            ("sale", "On Sale"),
            ("new", "When New"),
        ],
        default="manual",
        required=True,
        help="Defines how this ribbon is assigned to products:\n"
        "- Manually: You assign the ribbon manually to products.\n"
        "- Sale: Applied when the product is visibly on sale.\n"
        "- New: Applied based on the New period you will define.\n",
    )
    new_period = fields.Integer(default=30)

    @api.constrains("assign")
    def _check_assign(self):
        automatic = self.filtered(lambda ribbon: ribbon.assign != "manual")
        ribbons_by_assign = {}
        if automatic:
            ribbons_by_assign = self.search(
                [("assign", "in", automatic.mapped("assign"))]
            ).grouped("assign")
        for ribbon in automatic:
            if ribbons_by_assign.get(ribbon.assign, self.browse()) - ribbon:
                raise ValidationError(
                    _(
                        "Only one ribbon with the assign %s is allowed.",
                        dict(self._fields["assign"].selection).get(ribbon.assign),
                    )
                )

    def _get_css_classes(self):
        css_classes = ""
        match self.style:
            case "ribbon":
                css_classes += "o_wsale_ribbon"
            case "tag":
                css_classes += "o_wsale_badge"

        match self.position:
            case "left":
                css_classes += " o_left"
            case "right":
                css_classes += " o_right"
        return css_classes

    def _is_applicable_for(self, product, price_data):
        self.check_singleton()

        if (
            self.assign == "sale"
            and price_data
            and (
                (
                    "base_price" in price_data
                    and (price_data["base_price"] > price_data["price_reduce"])
                )
                or (
                    "compare_list_price" in price_data
                    and price_data["compare_list_price"] > price_data["price"]
                )
                or price_data.get("has_discounted_price")
            )
        ):
            return True
        if (  # noqa: SIM103  the condition reads as a checklist; a bare return would not
            self.assign == "new"
            and self.new_period >= (fields.Datetime.today() - product.publish_date).days
        ):
            return True
        return False
