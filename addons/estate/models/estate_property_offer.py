from dateutil.relativedelta import relativedelta
from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare

class estate_property_offer(models.Model):
    _name = "estate.property.offer"
    _description = "Test Model tag"
    _order = "price desc"


    name = fields.Char(required=True)
    price = fields.Float(string="price")
    status = fields.Selection(
        selection=[
            ("accepted", "Accepted"),
            ("refused", "Refused"),
        ],
        string="Status",
        copy=False,
        default=False,
    )
    partner_id = fields.Many2one('res.partner', string='partner', required=True)
    property_id = fields.Many2one('estate.property', string='property', required=True)
    create_date = fields.Date()
    date_deadline = fields.Date(string="Deadline", compute="_compute_date_deadline", inverse="_inverse_date_deadline",store=True)
    validity = fields.Integer(string="Validity (days)", default=7)


# this function user can add date with deadline and can enter how many days .
    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for offer in self:
            date = offer.create_date if offer.create_date else fields.Date.today()
            offer.date_deadline = date + relativedelta(days=offer.validity)

    def _inverse_date_deadline(self):
        for offer in self:
            date = offer.create_date if offer.create_date else fields.Date.today()
            offer.validity = (offer.date_deadline - date).days

    # this function user can sccept offer or refuse the status will be shaw
    # once he accepted the name of buyer and selingprice will be for the offer accpted
    # and the state will be offers accepted .

    def action_accept(self):
        if "accepted" in  self.mapped("property_id.offer_ids.status"):
            raise UserError("An offer as already been accepted.")
        self.write(
            {
                "status": "accepted",
            }
        )
        return self.mapped("property_id").write(
            {
                "state": "offer_accepted",
                "selingPrice": self.price,
                "buyerid": self.partner_id.id,
            }
        )

    def action_refuse(self):
        return self.write(
            {
                "status": "refused",
            }
        )


    _sql_constraints = [
        ('check_percentage3', 'CHECK(price > 0 )',
         'The price should be  >0')
    ]

    @api.model
    def create(self, vals):
        if vals.get("property_id") and vals.get("price"):
            prop = self.env["estate.property"].browse(vals["property_id"])
            # We check if the offer is higher than the existing offers
            if prop.offer_ids:
                max_offer = max(prop.mapped("offer_ids.price"))
                if float_compare(vals["price"], max_offer, precision_rounding=0.01) <= 0:
                    raise UserError("The offer must be higher than %.2f" % max_offer)
            prop.state = "offer_received"
        return super().create(vals)





