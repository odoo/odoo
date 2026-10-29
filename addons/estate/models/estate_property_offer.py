# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


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
