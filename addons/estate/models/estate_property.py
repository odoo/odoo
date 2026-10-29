# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
