# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero


class EstateProperty(models.Model):
    """A property put on sale by the agency: a house, an apartment, a piece of land, ..."""

    # The technical name identifies the model everywhere (views, access rights, relations); the ORM
    # derives the table name from it by replacing dots with underscores: `estate_property`
    _name = "estate.property"
    _description = "Real Estate Property"

    name = fields.Char(string="Title", required=True)
    description = fields.Text(string="Description")
    postcode = fields.Char(string="Postcode")
    # A lambda default is evaluated at each record creation, not once when the server starts
    date_availability = fields.Date(
        string="Available From",
        default=lambda self: fields.Date.add(fields.Date.context_today(self), months=3),
        copy=False,
    )
    # Float is enough for a training app; a real one would use a Monetary field with a currency
    expected_price = fields.Float(string="Expected Price", required=True)
    # Read-only for the user: it is set when an offer is accepted
    selling_price = fields.Float(string="Selling Price", readonly=True, copy=False)
    bedrooms = fields.Integer(string="Bedrooms", default=2)
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer(string="Facades")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Garden")
    garden_area = fields.Integer(string="Garden Area (sqm)")
    # Computed fields are not stored by default: they are computed on the fly when read
    total_area = fields.Integer(string="Total Area (sqm)", compute="_compute_total_area")
    # The database stores the key (e.g. 'north'); the user sees the label (e.g. "North")
    garden_orientation = fields.Selection(
        string="Garden Orientation",
        selection=[("north", "North"), ("south", "South"), ("east", "East"), ("west", "West")],
    )
    # Reserved name: records with active=False are archived and hidden from searches by default
    active = fields.Boolean(string="Active", default=True)
    state = fields.Selection(
        string="Status",
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("cancelled", "Cancelled"),
        ],
        default="new",
        required=True,
        copy=False,
    )

    # Many2one: a column holding the id of one record of the comodel (a foreign key)
    property_type_id = fields.Many2one(string="Property Type", comodel_name="estate.property.type")
    # Set from the accepted offer, hence read-only and not copied
    partner_id = fields.Many2one(
        string="Buyer", comodel_name="res.partner", readonly=True, copy=False
    )
    # The salesperson is the user creating the property, unless changed
    user_id = fields.Many2one(
        string="Salesperson", comodel_name="res.users", default=lambda self: self.env.user
    )
    # Many2many: stored in a separate relation table, each side can link to many records
    tag_ids = fields.Many2many(string="Tags", comodel_name="estate.property.tag")
    # One2many: no column; it is the reverse of the `property_id` Many2one on the offers
    offer_ids = fields.One2many(
        string="Offers", comodel_name="estate.property.offer", inverse_name="property_id"
    )
    best_price = fields.Float(string="Best Offer", compute="_compute_best_price")

    # SQL constraints are enforced by PostgreSQL itself, whatever the origin of the data
    _check_expected_price = models.Constraint(
        "CHECK(expected_price > 0)", "The expected price must be strictly positive."
    )
    _check_selling_price = models.Constraint(
        "CHECK(selling_price >= 0)", "The selling price cannot be negative."
    )

    # ------------------------------------------------------------
    # CONSTRAINT METHODS
    # ------------------------------------------------------------

    # Python constraints cover rules SQL cannot express; they run when a listed field is written
    @api.constrains("expected_price", "selling_price")
    def _check_selling_price_ratio(self):
        for estate_property in self:
            # A zero selling price means that no offer was accepted yet: nothing to check
            if float_is_zero(estate_property.selling_price, precision_digits=2):
                continue
            # Floats are never compared with == or <: 0.1 + 0.2 != 0.3 in binary floating point
            minimum_price = estate_property.expected_price * 0.9
            if float_compare(estate_property.selling_price, minimum_price, precision_digits=2) < 0:
                raise ValidationError(
                    self.env._(
                        "The selling price must be at least 90%% of the expected price: %(price)s.",
                        price=minimum_price,
                    )
                )

    # ------------------------------------------------------------
    # COMPUTE AND ONCHANGE METHODS
    # ------------------------------------------------------------

    # A compute method receives a recordset: it must loop and assign the field on every record
    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for estate_property in self:
            estate_property.total_area = estate_property.living_area + estate_property.garden_area

    # A dotted dependency also triggers the recompute when an offer's price changes
    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for estate_property in self:
            estate_property.best_price = max(estate_property.offer_ids.mapped("price"), default=0.0)

    @api.onchange("garden")
    def _onchange_garden(self):
        """Suggest typical garden values when the garden is ticked, and clear them when unticked.

        An onchange only runs in the form view, before saving, and the user can still change the
        suggested values. Code creating properties directly is not affected.
        """
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = 0
            self.garden_orientation = False

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    # Called by the buttons of the form view; a business rule violation raises a UserError, which
    # the web client shows as a dialog, and rolls the transaction back
    def action_sold(self):
        for estate_property in self:
            if estate_property.state == "cancelled":
                raise UserError(self.env._("A cancelled property cannot be sold."))
            if estate_property.state != "offer_accepted":
                raise UserError(self.env._("Accept an offer before selling the property."))
        self.state = "sold"

    def action_cancel(self):
        if any(estate_property.state == "sold" for estate_property in self):
            raise UserError(self.env._("A sold property cannot be cancelled."))
        self.state = "cancelled"
