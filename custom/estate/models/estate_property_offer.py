from email.policy import default

from dateutil.utils import today

from odoo import models, fields ,api
from datetime import date, timedelta

from odoo.exceptions import UserError


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "represents the offers that the buyers makes which will be received by the salesman"
    _order = "price desc"
    partner = fields.Many2one(
        "res.partner",
        required= True
    )
    property = fields.Many2one(
        "estate.property",
        required= True
    )
    # property_type_id= fields.Char(
    #     related="estate_property_id.property_type_id",
    #     stored=True
    #     )


    price = fields.Float(
        required=True
    )

    state = fields.Selection(
        selection=[
            ('accepted', 'Accepted'),
            ('refused', 'Refused'),
            ('proposed', 'Proposed'),
        ],
        default='proposed',
        string='Status'
    )

    deadline = fields.Date(
        default=lambda self: fields.Date.today() + timedelta(days=30)
    )
    validitydate = fields.Integer(
        compute="_compute_validity_date",
        inverse="_inverse_validity_date",
        string="Days Remaining",
        default=7,
        store = True  # use store so you can in the future search about it
        # the odoo ignore searching about computed fields like this and
        # and also , it did not save it in the database
    )

    @api.depends('deadline')
    def _compute_validity_date(self):
        today = fields.Date.today()
        for record in self:
            if record.deadline:
                record.validitydate = (record.deadline - today).days
            else:
                record.validitydate = 0

    def _inverse_validity_date(self):
        today = fields.Date.today()
        for record in self:
            if record.validitydate:
                record.deadline = today + timedelta(days=record.validitydate)
            else:
                record.deadline = False

    def action_confirm(self):
        for offer in self:
            if offer.state != 'proposed':
                raise UserError("Only proposed offers can be accepted!")

            # Update property information
            offer.property.write({
                'Selling_Price': offer.price,
                'buyer': offer.partner.id,
                'Status': 'offerAccepted'
            })

            # Update offer state
            offer.state = 'accepted'

            # Refuse other offers
            self.search([
                ('property', '=', offer.property.id),
                ('id', '!=', offer.id),
                ('state', '=', 'proposed')
            ]).write({'state': 'refused'})
        return True

    def action_cancel(self):
        for offer in self:
            if offer.state == "proposed":
                offer.state = "refused"

            else:
                raise UserError("Can not Change the offer form accepted to refused")

    _sql_constraints = [
        ('check_price','CHECK(price>=0)','The price should be Positive')
    ]

    #important to memorize
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            prop = self.env['estate.property'].browse(vals['property'])  # 1,2

            # 1) Set the property state to “Offer Received”
            if prop.Status == "new":
                prop.Status = 'offerReceived'

            # 2) Raise if the new price is lower than any existing offer
            max_price = max(prop.offer.mapped('price') or [0])  # 3
            if vals.get('price', 0) < max_price:
                raise UserError(
                    f"The offer amount must be higher than the current best offer "
                    f"({max_price})."
                )

        return super().create(vals_list)