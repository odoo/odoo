#from odoo.exceptions import ValidationError
#from odoo import api, fields, models
from odoo import fields, models

DEFAULT_MESSAGE = "Default message"

SUCCESS = "success"
DANGER = "danger"
WARNING = "warning"
INFO = "info"
DEFAULT = "default"

class InheritedModel(models.Model):
    _inherit = "res.users"
    trip_ids = fields.One2many('car.pooling', "driver")
    my_book_trip_ids = fields.One2many('car.pooling.passenger', "passenger")
    phone_number = fields.Char()
    is_volunteer = fields.Selection(
        string="Are you volunteer to participate in Car pooling?",
        selection=[("no", "No"), ("yes", "Yes")],
        default="yes",
        readonly=True)
    car_name = fields.Char(string="Vehicle Name", required=True, default="Unkown")
    Car_model = fields.Char(string="Vehicle Model", help="It is to specify the vehicle model like BMW 218i Gran Coupe")
    car_type = fields.Selection(
        string="Vehicle Type",
        selection=[("SUv", "SUV"), ("Hatchback", "Hatchback"), ("Crossover", "Crossover"), ("Convertible", "Convertible"), ('Sedan', 'Sedan'), ('Sports_Car', 'Sports Car'),
        ('Coupe', 'Coupe'), ('Minivan', 'Minivan'), ('Station_Wagon', 'Station Wagon'), ('Pickup_Truck', 'Pickup Truck')],
        default="Sedan")
    car_plate_number = fields.Char(string="Vehicle plate Number", required=True, default="Unkown")
    car_color = fields.Char(string="Vehicle Color", help="Choose your color")
    Car_image = fields.Binary("Upload Vehicle Image", attachment=True, store=True, help="This field holds the vehicle image ")

    # @api.constrains('phone_number')
    # def _check_phone_number(self):
    #     for record in self:
    #         if record.phone_number != '':
    #             if not str(record.phone_number).isdigit() or len(record.phone_number) != 10:
    #                 raise ValidationError("Cannot enter invalid phone number")
    #     return True
