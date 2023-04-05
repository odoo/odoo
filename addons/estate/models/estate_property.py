from odoo import api, fields, models
from dateutil.relativedelta import relativedelta

from odoo.exceptions import UserError, ValidationError
class estate_property(models.Model):
    _name = "estate.property"
    _description = "Test Model"
    _order = "id desc"
    _sql_constraints = [
        ('check_percentage', 'CHECK(expected_price > 0 )',
         'The expected_price should be  >0')
    ]

    name = fields.Char(required=True)
    expected_price = fields.Float(required=True)
    title = fields.Char(string="Title")
    description = fields.Char(string="description")
    postcode = fields.Integer(string="postcode")
    bedrooms = fields.Integer(string="bedrooms")
    facades = fields.Integer(string="facades")
    garden = fields.Boolean(default=True,string="garden")
    gardenorientation = fields.Selection([('north', 'north'), ('west', 'west'), ('sauth', 'sauth')],string="gardenorientation",store=True)
    active = fields.Boolean(default=True)

    def _default_date_availability(self):
        return fields.Date.context_today(self) + relativedelta(months=3)

    date_availability = fields.Date("Available From", default=lambda self: self._default_date_availability(),
                                    copy=False)
    selingPrice = fields.Float(readonly=True,string="selingPrice")
    livingarea = fields.Integer(string="livingarea")
    garage = fields.Boolean(default=True,string="garage")
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("offer_received", "Offer Received"),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ("canceled", "Canceled"),
        ],
        string="Status",
        required=True,
        copy=False,
        default="new",
    )
    buyerid = fields.Many2one('res.partner', string='buyer person',copy=False)
    userid = fields.Many2one('res.users', string='Sales person', default=lambda self: self.env.uid)
    property_type_id = fields.Many2one("estate.property.type",string="property type ")
    tag_ids = fields.Many2many("estate.property.tag", string="Tag ")
    offer_ids = fields.One2many("estate.property.offer", "property_id", string="Offer")
    total_area = fields.Float(compute="_compute_total_area")
    best_price = fields.Float(compute="_compute_max",store=True)
    property_type_id = fields.Many2one("estate.property.type", string="Property Type")

# this function for users so if users click on selcted field dirct
    # will give him defulte value in fail linked to field
    @api.onchange("garden")
    def _onchange_garden(self):    # _ this means privte method at the begain of the line
        # if the garden = True
        if self.garden:
            self.gardenorientation = "north"
        else:
            self.gardenorientation = False
            
# this function will give the user the sum for to field
    @api.depends("bedrooms","livingarea")
    def _compute_total_area(self):
        for record in self:
            record.total_area= record.bedrooms + record.livingarea


#this function will give the user the best price from  all the offer
    @api.depends("offer_ids.price")
    def _compute_max(self):
        for record in self:
            record.best_price = max(record.mapped("offer_ids.price"),default=0)

    # this function will give the user action if  choose canceled  can't make it sold
    # also if he schoose sold cant be canceled
    @api.depends("canceled,sold")
    def action_sold(self):
        if "canceled" in self.mapped("state"):
            raise UserError("Canceled properties cannot be sold.")
        return self.write({"state": "sold"})

    def action_cancel(self):
        if "sold" in self.mapped("state"):
            raise UserError("Sold properties cannot be canceled.")
        return self.write({"state": "canceled"})

   # _sql_constraints = [
    #    ('check_percentage2', 'CHECK(selingPrice > 0 ) ',
    #     'The selingPrice should be  >0')
   #]

    @api.constrains('selingPrice')
    def _check_date_end(self):
        for record in self:
            if record.selingPrice <= record.expected_price - 0.1:
                raise ValidationError("selling price cannot be lower than 90% of the expected price.")

    @api.ondelete(at_uninstall=False)
    def _unlink_if_new_or_canceled(self):
        if not set(self.mapped("state")) <= {"new", "canceled"}:
            raise UserError("Only new and canceled properties can be deleted.")

