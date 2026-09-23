from odoo import api, fields, models


class FleetVehicle(models.Model):
    _name = 'fleet_training.vehicle'
    _description = 'Fleet Vehicle'
    _order = 'name'

    name = fields.Char(required=True, help="Internal fleet reference, e.g. 'Fleet-001'.")
    license_plate = fields.Char()
    vin_sn = fields.Char(string="Chassis Number")
    color = fields.Char()
    model_year = fields.Integer(string="Model Year")
    seats = fields.Integer(default=5)
    acquisition_date = fields.Date()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    driver_id = fields.Many2one('fleet_training.driver', string="Assigned Driver")
    category_id = fields.Many2one('fleet_training.category', string="Category")
    tag_ids = fields.Many2many('fleet_training.tag', string="Tags")

    age_years = fields.Integer(string="Fleet Age (years)", compute='_compute_age_years', store=True)

    state = fields.Selection(
        [
            ('available', 'Available'),
            ('assigned', 'Assigned'),
            ('maintenance', 'In Maintenance'),
        ],
        string="Status", default='available', required=True,
    )

    def action_set_maintenance(self):
        self.state = 'maintenance'

    def action_set_available(self):
        self.state = 'available'

    @api.depends('acquisition_date')
    def _compute_age_years(self):
        today = fields.Date.context_today(self)
        for vehicle in self:
            if not vehicle.acquisition_date:
                vehicle.age_years = 0
                continue
            acquired = vehicle.acquisition_date
            years = today.year - acquired.year
            if (today.month, today.day) < (acquired.month, acquired.day):
                years -= 1
            vehicle.age_years = max(years, 0)

    @api.onchange('driver_id')
    def _onchange_driver_id(self):
        if self.driver_id and not self.driver_id.phone:
            return {
                'warning': {
                    'title': self.env._("Missing contact info"),
                    'message': self.env._(
                        "%(driver)s has no phone number on file. "
                        "Consider adding one before assigning this vehicle.",
                        driver=self.driver_id.name,
                    ),
                }
            }
