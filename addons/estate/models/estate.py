from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class RealEstate(models.Model):
    _name = "estate_property"
    _description = "Estate property"
    _order = "id desc"

    name = fields.Char(required=True)
    description = fields.Text()
    postcode = fields.Char()
    date_availability = fields.Date(
        copy=False, default=fields.Date.add(fields.Date.today(), months=3)
    )
    expected_price = fields.Float(required=True)
    selling_price = fields.Float(readonly=True, copy=False)
    bedrooms = fields.Integer(default=2)
    living_area = fields.Integer()
    facades = fields.Integer()
    garage = fields.Boolean()
    garden = fields.Boolean()
    garden_area = fields.Integer(default=10)
    garden_orientation = fields.Selection(
        [("north", "North"), ("south", "South"), ("east", "East"), ("west", "West")],
        default="north",
    )
    active = fields.Boolean(default=True)
    state = fields.Selection(
        [
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("cancelled", "Cancelled"),
        ],
        default="new",
        copy=False,
        required=True,
    )
    property_type = fields.Many2one("estate.property.type")
    salesman = fields.Many2one("res.users", default=lambda self: self.env.user)
    buyer = fields.Many2one("res.partner")
    tag_ids = fields.Many2many("estate.property.tag", string="Tags")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offers")
    price = fields.Float(related="offer_ids.price", string="Price", readonly=True)
    status = fields.Selection(
        related="offer_ids.status", string="Status", readonly=True
    )
    partner_id = fields.Many2one(
        related="offer_ids.partner_id", string="Partner", readonly=True
    )
    total_area = fields.Float(compute="_compute_area")
    best_price = fields.Float(compute="_compute_best_price")

    _sql_constraints = [
        (
            "check_expected_price",
            "CHECK(expected_price >= 0)",
            "A property expected price must be strictly positive",
        ),
        (
            "check_selling_price",
            "CHECK(selling_price >= 0)",
            "A property selling price must be positive",
        ),
    ]

    # Calculate total area
    @api.depends("living_area", "garden_area")
    def _compute_area(self):
        for record in self:
            record.total_area = record.living_area + record.garden_area

    # Show highest price
    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for record in self:
            record.best_price = max(record.offer_ids.mapped("price") or [0])

    # Set default values of garden_area and orientation when garden is checked
    @api.onchange("garden", "garden_area", "garden_orientation")
    def _onchange_garden_value(self):
        if self.garden == True:
            self.garden_area = self.garden_area or 10
            self.garden_orientation = self.garden_orientation or "north"
        else:
            self.garden_area = 0
            self.garden_orientation = False

    # Sold action
    def action_sold(self):
        for record in self:
            if record.state != "cancelled":
                record.state = "sold"
            else:
                raise UserError("Property that is cancelled cannot be set to sold")
        return True

    # Cancel action
    def action_cancel(self):
        for record in self:
            if record.state != "sold":
                record.state = "cancelled"
            else:
                raise UserError("Property that is sold cannot be cancelled")
        return True

    @api.constrains("selling_price")
    def _check_selling_price(self):
        for record in self:
            min_price = record.expected_price * 0.9

            if (
                float_compare(record.selling_price, min_price, precision_rounding=0.01)
                == -1
            ):
                raise ValidationError(
                    "Selling price cannot be lower than 90% of the expected price"
                )

    # Prevent deletion of property which is not in 'new' or 'cancelled' state
    # @api.ondelete(at_uninstall=False)
    def unlink(self):
        for record in self:
            if record.state not in ("new", "cancelled"):
                raise UserError(
                    "You cannot delete a property that is not in 'New' or 'Cancelled' state"
                )
        return super().unlink()
