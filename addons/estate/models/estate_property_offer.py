# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EstatePropertyOffer(models.Model):
    """A price proposed by a potential buyer for a property."""

    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"

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
    validity = fields.Integer(string="Validity (days)", default=7)
    # The deadline and the validity describe the same thing: editing either one updates the other
    date_deadline = fields.Date(
        string="Deadline", compute="_compute_date_deadline", inverse="_inverse_date_deadline"
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
