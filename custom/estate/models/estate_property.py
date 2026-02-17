
from email.policy import default
from reportlab.lib.utils import rl_isdir

from odoo.exceptions import UserError
from odoo import models, fields ,api
from datetime import  date

from odoo.tools import float_compare
from odoo.tools.float_utils import float_is_zero ,float_split_str
from odoo.addons.test_convert.tests.test_env import record


class EstateProperty(models.Model):
    _name = "estate.property"
    _description = "testing the estate date table"
    _inherit = ['mail.thread']
    _order = "id desc"

    name = fields.Char()
    description= fields.Char()
    Postcode = fields.Integer(size=4)
    Expected_Price= fields.Float(
        string="Expected Price",
        default= "0.00",
    )
    BedRooms = fields.Integer(
        string="Bed rooms",
        defult=2
    )
    Facades = fields.Integer(
        default=0
    )
    Garden = fields.Boolean(
        default = False
    )

    Garden_area= fields.Integer(
        string="Garden Area (sqm)",
        default=0
    )

    Garden_Orentation=fields.Selection(
        selection=[
            ('north', 'North'),
            ('south', 'South'),
            ('west', 'West'),
            ('east', 'East'),

        ],
        string="Garden Orentation"
    )

    @api.onchange("Garden")
    def _onchange_Garden(self):
        for record in self:
            if self.Garden == True:
                self.Garden_Orentation = "north"
                self.Garden_area = 10
                return {'warning': {
                    'title': ("Garden Setted True"),
                    'message': ('You need to Set the area and orentation of the garden')}}
            else:
                self.Garden_Orentation = None
                self.Garden_area = 0

    Active = fields.Boolean(
        default = True
    )
    Avaible_Form= fields.Date(
        default=date.today(),
        copy = False
    )

    location= fields.Char()
    Selling_Price= fields.Float(
        string = "Selling Price",
        default = 0.00,
        readonly = True,
        copy = False
    )
    LivingArea = fields.Integer(
        stirng= "Living Area (sqm)",
        default = 0
    )
    Grage = fields.Boolean(
        default= False
    )
    Status= fields.Selection(
        selection=[
            ('new','New'),
            ('old','Old'),
            ('offerReceived','Offer Received'),
            ('offerAccepted','Offer Accepted'),
            ('sold','Sold'),
            ('cancelled','Cancelled'),
        ],
        default='new'
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible User',
        default=lambda self: self.env.user
    )

    property_type_id = fields.Many2one(
        'estate.property.type',
        # default=lambda self: self.env.estate.porpert.type
    )

    seller = fields.Many2one(
        "res.partner",
        string="sales man"

    )
    buyer = fields.Many2one(
        "res.partner",
        string="buyer"
    )
    expected_price=fields.Float(
    )

    tags= fields.Many2many(
        'estate.property.tag',
    )

    offer= fields.One2many(
        'estate.property.offer',
        # this the model you need to inverse the relation with
        'property',
        ondelete="cascade"
        # foucse on the inverse_name it should mached with the attrubite of the offer class
    )

    total_offers= fields.Integer(
        compute="_compute_the_offers",
        readonly= True,
        string="Offers recived"
    )

    @api.depends('offer')
    def _compute_the_offers(self):
        for record in self:
            record.total_offers = len(record.offer)

    best_offer= fields.Float(
        compute="_compute_best_offer",
        readonly=True,
        string="Best Selling Offer",
        stored=True,
    )

    @api.depends('offer.price')
    def _compute_best_offer(self):
        for record in self:
            offer_price=record.offer.mapped('price')

        if offer_price:
            record.best_offer=max(offer_price)
        else:
            record.best_offer = 0.0

    total_areas= fields.Integer(
        string="Total Areas",
        readonly=True,
        compute="_compute_total_area"
    )

    @api.depends('LivingArea','Garden_area')
    def _compute_total_area(self):
        for record in self:
            record.total_areas=record.LivingArea+record.Garden_area


    # it should be declared without _ which means that it is a public method
    # Also you should return something so the odoo will know that the fucntion is done
    def sold_property(self):
        for record in self:
            if record.Status != "cancelled":
                record.Status = "sold"
            else:
                raise UserError("Can Not Sold Property After it cancelled")
            return True



    def cancel_property(self):
        for record in self:
            if record.Status !="sold":
                record.status= "cancelled"

            else:
                raise UserError("Can Not cancelled Property After it sold")
            return True

    _sql_constraints = [
        # ('dubplicate_Names','UNIQUE(name)','Can not dubplicate other property Name')
        ('dubplicate_Names','CHECK(expected_price >= 0)','The Expected Price Can not be nagative')
    ]
    #

    @api.constrains('Selling_Price')
    def _check_selling_price(self):
        for record in self:
            if not float_is_zero(record.Selling_Price,precision_digits=2):
                less_selling_price = record.Expected_Price * 0.9
                if float_compare(record.Selling_Price,less_selling_price,precision_digits=2) == -1:
                    raise UserError("Offer price must be at least 90% of the expected price!")


    # date_availability = fields.Char(
    # )
    # becomes correct
    @api.ondelete(at_uninstall=False)
    def _unlink_except_not_new_or_cancelled(self):
        for prop in self:
            if prop.Status not in ('new', 'cancelled'):
                raise UserError(
                    "Only properties in state 'New' or 'Cancelled' can be deleted."
                )