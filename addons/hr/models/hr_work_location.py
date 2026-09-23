from odoo import fields, models


class HrWorkLocation(models.Model):
    _name = "hr.work.location"
    _description = "Work Location"
    _order = "name"

    active = fields.Boolean(default=True)
    name = fields.Char(
        string="Work Location",
        required=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    location_type = fields.Selection(
        selection=[("home", "Home"), ("office", "Office"), ("other", "Other")],
        string="Location Type",
        default="office",
        required=True,
    )
    address_id = fields.Many2one(
        comodel_name="res.partner",
        string="Work Address",
        required=True,
        check_company=True,
    )
    location_number = fields.Char()
