# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class EstatePropertyOffer(models.Model):
    """A price proposed by a potential buyer for a property."""

    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"
    _order = "price desc"

    price = fields.Float(string="Price")
    # Empty while the offer waits for the agent's decision
    status = fields.Selection(
        string="Status", selection=[("accepted", "Accepted"), ("refused", "Refused")], copy=False
    )
    partner_id = fields.Many2one(string="Partner", comodel_name="res.partner", required=True)
    # Deleting a property deletes its offers: they have no meaning without it
    property_id = fields.Many2one(
        string="Property", comodel_name="estate.property", ondelete="cascade", required=True
    )
    # Stored so that offers can be searched by type, which the stat button of the type form needs
    property_type_id = fields.Many2one(related="property_id.property_type_id", store=True)
    validity = fields.Integer(string="Validity (days)", default=7)
    # The deadline and the validity describe the same thing: editing either one updates the other
    date_deadline = fields.Date(
        string="Deadline", compute="_compute_date_deadline", inverse="_inverse_date_deadline"
    )

    _check_price = models.Constraint(
        "CHECK(price > 0)", "The offer price must be strictly positive."
    )

    # ------------------------------------------------------------
    # COMPUTE METHODS
    # ------------------------------------------------------------

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for offer in self:
            offer.date_deadline = fields.Date.add(offer._get_validity_start(), days=offer.validity)

    def _inverse_date_deadline(self):
        """Store the deadline chosen by the user as a number of validity days."""
        for offer in self:
            if offer.date_deadline:
                offer.validity = (offer.date_deadline - offer._get_validity_start()).days

    def _get_validity_start(self):
        """Return the date from which the validity is counted: the creation date of the offer.

        `create_date` is only set once the record is saved, so a new offer counts from today.
        """
        self.ensure_one()
        return fields.Date.to_date(self.create_date) or fields.Date.context_today(self)

    # ------------------------------------------------------------
    # CRUD METHODS
    # ------------------------------------------------------------

    # create() receives a list of values, one dict per record: the ORM creates them in batch
    @api.model_create_multi
    def create(self, vals_list):
        """Refuse offers on closed properties or below the best offer, then flag the properties
        as having received an offer."""
        for vals in vals_list:
            estate_property = self.env["estate.property"].browse(vals.get("property_id"))
            if estate_property.state in ("offer_accepted", "sold", "cancelled"):
                raise UserError(self.env._("This property no longer accepts offers."))
            best_price = estate_property.best_price
            if float_compare(vals.get("price", 0.0), best_price, precision_digits=2) < 0:
                raise UserError(
                    self.env._(
                        "The offer must be at least the best offer: %(price)s.", price=best_price
                    )
                )
        # super() runs the standard creation, including the overrides of other addons
        offers = super().create(vals_list)
        offers.property_id.filtered(lambda p: p.state == "new").state = "offer_received"
        return offers

    # ------------------------------------------------------------
    # ACTION METHODS
    # ------------------------------------------------------------

    def action_accept(self):
        """Accept the offer: its partner becomes the buyer and its price the selling price."""
        for offer in self:
            estate_property = offer.property_id
            if estate_property.state in ("sold", "cancelled"):
                raise UserError(self.env._("Offers on a sold or cancelled property are closed."))
            if "accepted" in estate_property.offer_ids.mapped("status"):
                raise UserError(self.env._("Another offer was already accepted for this property."))
            offer.status = "accepted"
            # One write() call updates the three fields in a single SQL query
            estate_property.write({
                "partner_id": offer.partner_id.id,
                "selling_price": offer.price,
                "state": "offer_accepted",
            })

    def action_refuse(self):
        if "accepted" in self.mapped("status"):
            raise UserError(self.env._("An accepted offer cannot be refused."))
        self.status = "refused"
