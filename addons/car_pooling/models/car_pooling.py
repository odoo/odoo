from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class CarPooling(models.Model):
    _name = "car.pooling"
    _description = "Trips"
    _order = "id desc"
    driver = fields.Many2one('res.users', required=True, readonly=True, string='Driver (Car owner)', index=True, default=lambda self: self.env.user)
    source_city = fields.Char(required=True)
    source_address = fields.Char(required=True)
    destination_city = fields.Char(required=True)
    destination_address = fields.Char(required=True)
    departure_date = fields.Datetime(string="Departure Date and Time", required=True)
    comments = fields.Text(help="The comments for the trips", string="Driver's Comments")
    tag = fields.Many2many("car.pooling.tag", string="Tags")
    is_round_trip = fields.Boolean(string="Round Trip")
    return_date = fields.Datetime(string="Return Date and Time")

    passenger_ids = fields.One2many("car.pooling.passenger", "trip_id", string="Passengers")

    comments_ids = fields.One2many("car.pooling.comment", "trip_id", string="Comments")
    capacity = fields.Integer(string="Number of seats", required=True)
    filled_seat = fields.Integer(string="Number of filled seats", readonly=True)
    available_seat = fields.Integer(compute="_compute_available_seat", store=True, string="Available seats")
    @api.depends("capacity", "filled_seat")
    def _compute_available_seat(self):
        for record in self:
            record.available_seat = record.capacity - record.filled_seat
    status = fields.Selection(
        string="Status",
        selection=[("available", "Available"), ("full", "Full"), ("unavailable", "Unavailable"), ("departed", "Departed"), ('canceled', 'Canceled')],
        default="available")

    name = fields.Char(compute="_compute_name")
    @api.depends('source_city', "destination_city")
    def _compute_name(self):
        for record in self:
            if record.source_city and record.destination_city:
                record.name = "From " + str(record.source_city) + " to " + str(record.destination_city)
            else:
                record.name = ""


    driver_uid = fields.Integer(compute="_get_driver_uid", store=True)
    @api.depends('driver')
    # adopted from https://github.com/hlibioulle/OpenWeek-odoo-carpooling/blob/main/carpooling/models/vehicle_trip.py
    def _get_driver_uid(self):
        for record in self:
            record.driver_uid = record.driver.id

    #TODO complete unavailable status
    # @api.depends('departure_date',"departure_time")
    # def _compute_unavailable_state(self):
    #     for record in self:
    #         now =datetime.datetime.now()
    #         if record.departure_date < now:
    #             record.status = "unavailable"

    is_current_user_driver = fields.Boolean(compute="_is_current_user_driver")
    @api.depends('driver')
    # adopted from https://github.com/hlibioulle/OpenWeek-odoo-carpooling/blob/main/carpooling/models/vehicle_trip.py
    def _is_current_user_driver(self):
        for record in self:
            record.is_current_user_driver = (record.driver == self.env.user)

    current_user_is_passenger = fields.Boolean(compute="_compute_current_user_is_passenger")
    @api.depends("passenger_ids")
    # adopted from https://github.com/hlibioulle/OpenWeek-odoo-carpooling/blob/main/carpooling/models/vehicle_trip.py
    def _compute_current_user_is_passenger(self):
        for record in self:
            record.current_user_is_passenger = (self.env.user in record.passenger_ids.passenger)

    current_user_book_status = fields.Char(compute="_compute_current_user_book_status", string="Booking status")
    def _compute_current_user_book_status(self):
        for record in self:
            record.current_user_book_status = "Undecided"
            for record2 in record.passenger_ids:
                if record2.passenger == self.env.user:
                    if record2.status == "accepted" or record2.status == "refused":
                        record.current_user_book_status = record2.status.capitalize()
                    break

    is_volunteer = fields.Char(compute="_is_volunteer")
    @api.depends('driver')
    def _is_volunteer(self):
        for record in self:
            record.is_volunteer = record.driver.is_volunteer

    car_name = fields.Char(compute="_car_name")
    @api.depends('driver')
    def _car_name(self):
        for record in self:
            record.car_name = record.driver.car_name

    Car_model = fields.Char(compute="_car_model")
    @api.depends('driver')
    def _car_model(self):
        for record in self:
            record.Car_model = record.driver.Car_model

    car_type = fields.Char(compute="_car_type")
    @api.depends('driver')
    def _car_type(self):
        for record in self:
            record.car_type = record.driver.car_type

    car_plate_number = fields.Char(compute="_car_plate_number")
    @api.depends('driver')
    def _car_plate_number(self):
        for record in self:
            record.car_plate_number = record.driver.car_plate_number

    car_color = fields.Char(compute="_car_color")
    @api.depends('driver')
    def _car_color(self):
        for record in self:
            record.car_color = record.driver.car_color

    Car_image = fields.Binary(attachment=True, store=True, compute="_car_image")
    @api.depends('driver')
    def _car_image(self):
        for record in self:
            record.Car_image = record.driver.Car_image

    def cancel_action(self):
        # This function is responsible for canceling a trip if the trip is not in "departed" status.
        for record in self:
            if record.status == "departed":
                raise UserError("The departed trip cannot be canceled")
            else:
                record.status = "canceled"

    def depart_action(self):
        # This function is responsible for changing the trip status to "departed" status.
        for record in self:
            if record.status == "canceled":
                raise UserError("The canceled trip cannot be in 'departed' status")
            else:
                record.status = "departed"
    #On write and On-delete and create api to avoid inconsistency (e.g., what if we update the capacity while it is in full status?)
    @api.model
    def create(self, vals):
        if vals['capacity'] == 0:
            raise UserError("The Number of seats (Vehicle Capacity) should be greater than zero!")
        return super(CarPooling, self).create(vals)
    @api.ondelete(at_uninstall=False)
    def _unlink_if_passenger_refused(self):
        if any(record.passenger_ids.status == "accepted" for record in self):
            msg = "There are some passengers in 'accepted' status for this trip. To delete the trip, please make sure you have refused all accepted book requests."
            raise UserError(msg)

    def write(self, vals):
        # on_write for updating capacity. (e.g., what if we update the capacity while it is in full status?)
        if "filled_seat" in vals and "capacity" in vals:
            if vals['capacity'] - vals['filled_seat'] == 0 and self.status not in ('unavailable', 'departed', 'canceled'):
                vals["status"] = 'full'
            elif vals['capacity'] - vals['filled_seat'] > 0  and self.status not in ('unavailable', 'departed', 'canceled'):
                vals["status"] = 'available'
        elif  "filled_seat" not in vals and "capacity" in vals:
            if vals['capacity'] - self.filled_seat == 0 and self.status not in ('unavailable', 'departed', 'canceled'):
                vals["status"] = 'full'
            elif vals['capacity'] - self.filled_seat > 0  and self.status not in ('unavailable', 'departed', 'canceled'):
                vals["status"] = 'available'
        elif "filled_seat" in vals and "capacity" not in vals:
            if self.capacity - vals['filled_seat'] == 0 and self.status not in ('unavailable', 'departed', 'canceled'):
                vals["status"] = 'full'
            elif self.capacity - vals['filled_seat'] > 0  and self.status not in ('unavailable', 'departed', 'canceled'):
                vals["status"] = 'available'
        super(CarPooling, self).write(vals)

    #Book and unbook action with its button such that it inserts the user to the passenger list or removes it from the list
    def book_or_unbook(self):
        for record in self:
            if self.env.user in record.passenger_ids.passenger:
                get_passenger_trip = self.env['car.pooling.passenger'].search([('passenger_uid', '=', str(self.env.user.id)), ('trip_id_id', '=', str(record.id))])
                if get_passenger_trip.status == "accepted":
                    msg = "You cannot unbook the trip because the book has been accepted by the driver. Contact " + str(record.driver.name) + " at " + str(record.driver.email) + " or by " + str(record.driver.phone_number) + " to ask booking refusal."
                    raise UserError(msg)
                get_passenger_trip.unlink()
            else:
                add_to_passenger = self.env['car.pooling.passenger']
                add_to_passenger.create({'passenger':self.env.user.id, 'trip_id':record.id, 'trip_date':record.departure_date, 'trip_driver':record.driver.name, 'is_round_trip':record.is_round_trip})
        return True

    _sql_constraints = [
        ('seat_no_check', 'CHECK(capacity >= 0)',
         'The seat number cannot be negative!'),
        ('available_seat_check', 'CHECK(filled_seat <= capacity)',
         "The capacity of the vehicle must be equal to or greater than the number of filled seats! To reduce the capacity, refuse some passengers' accepted requests.")]

    # python constraint for return date
    @api.constrains('return_date')
    def _check_return_date(self):
        for record in self:
            if record.is_round_trip:
                if record.return_date <= record.departure_date:
                    raise ValidationError("The return date and Time must be greater than the departure time!")


#############################################################
class CarPoolingTag(models.Model):
    _name = "car.pooling.tag"
    _description = "A trip tag is, for example, a trip which is ‘long’ or ‘short’."
    _order = "name"
    name = fields.Char(required=True)
    color = fields.Integer()
    _sql_constraints = [
       ('unique_tag', 'unique(name)', 'The tag name should be unique!')]

#############################################################

class CarPoolingPassenger(models.Model):
    _name = "car.pooling.passenger"
    _description = "Passenger"
    _order = "id desc"

    passenger = fields.Many2one('res.users', required=True, readonly=True, string='Passenger', index=True, default=lambda self: self.env.user)
    passenger_uid = fields.Integer(compute="_get_passenger_uid", store=True)
    @api.depends('passenger')
    def _get_passenger_uid(self):
        for record in self:
            record.passenger_uid = record.passenger.id

    trip_id = fields.Many2one('car.pooling', string="Trip", ondelete='cascade')
    trip_id_id = fields.Integer(compute="_get_trip_uid", store=True)
    @api.depends('trip_id')
    def _get_trip_uid(self):
        for record in self:
            record.trip_id_id = record.trip_id.id

    status = fields.Selection(string="Status", selection=[("accepted", "Accepted"), ("refused", "Refused")], help="The status of the trip offer")
    accept_count = fields.Integer(readonly=True, string="Number of Refusals")
    refuse_count = fields.Integer(readonly=True, string="Number of Acceptances")

    trip_date = fields.Datetime(string="Departure Date and Time", readonly=True)
    trip_driver = fields.Char(string="Driver", readonly=True)
    is_round_trip = fields.Boolean(string="Round Trip", readonly=True)


    _sql_constraints = [
        ('accept_count_check', 'CHECK(accept_count <= 2)',
         'You can only accept a booked trip for a passenger twice!'),
        ('refuse_count_check', 'CHECK(refuse_count <= 2)',
         "You can only refuse a booked trip for a passenger twice!"),
         ("single_booking_check", 'unique(trip_id, passenger)', 'A passenger can only book a trip once!')
        ]

    def action_accept(self):
        #TODO add automatic odoo message (Accpeted) sent to the passanger
        for record in self:
            if record.trip_id.status != "departed" and record.trip_id.status != "canceled":
                if record.trip_id.filled_seat < record.trip_id.capacity:
                    record.trip_id.filled_seat = record.trip_id.filled_seat+1
                    record.status = "accepted"
                    record.accept_count += 1
                    #TODO fix the notification issue
                    # record.passenger.user_id.notify_success(message="You booked trip accepted by the driver.")
                    if  record.trip_id.filled_seat == record.trip_id.capacity:
                        record.trip_id.status = "full"
                else:
                    raise UserError("The vehicle does not have capacity for more passengers.")
            else:
                raise UserError("No passenger can be added to a departed or canceled trip.")
        return True

    def action_refuse(self):
        #TODO add automatic odoo message (Refuse) sent to the passanger
        for record in self:
            if record.trip_id.status != "departed" and record.trip_id.status != "canceled":
                record.status = "refused"
                record.refuse_count += 1
                record.trip_id.filled_seat = record.trip_id.filled_seat - 1
                record.trip_id.status = "available"
            else:
                raise UserError("No passenger can be removed from a departed or canceled trip.")
        return True
    @api.ondelete(at_uninstall=False)
    def _unlink_if_passenger_refused(self):
        for record in self:
            if record.status == "accepted":
                if record.trip_id.status != 'departed':
                    msg = "The book has been accepted. To delete the book, the book request must be first refused by the drive."
                elif record.trip_id.status == 'departed':
                    msg = "The trip is in departed status. An accepted book request for a departed trip cannot be removed."
                raise UserError(msg)
##############################################################

# A model for driver-trip-passanger message should be added
AVAILABLE_PRIORITIES = [
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High')]
class CarPoolingPassengerComments(models.Model):
    _name = "car.pooling.comment"
    _description = "This model is for storing the comments written about a trip"
    _order = "id desc"
    passenger = fields.Many2one('res.users', required=True, readonly=True, string='Passenger', index=True, default=lambda self: self.env.user)
    trip_id = fields.Many2one('car.pooling', string="Trip", ondelete='cascade')
    comment = fields.Text()
    trip_star = fields.Selection(AVAILABLE_PRIORITIES, string="Star")

    passenger_uid = fields.Integer(compute="_get_passenger_uid", store=True)
    @api.depends('passenger')
    def _get_passenger_uid(self):
        for record in self:
            record.passenger_uid = record.passenger.id

    @api.ondelete(at_uninstall=False)
    def _unlink_if_the_same_passenger(self):
        for record in self:
            if record.passenger != self.env.user:
                msg = "You cannot remove somebody else's comment"
                raise UserError(msg)

    _sql_constraints = [
         ("single_booking_check", 'unique(trip_id,passenger)', 'A passenger can only pose one comment!')
        ]
