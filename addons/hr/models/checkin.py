from odoo import fields, models

class CheckIn(models.Model):
    _name = "hr.checkin"
    _description = "Check in status of each employees"

    checkin_status = fields.Boolean("Check-In Status", readonly=True)

    time_checkin = fields.Datetime("Time Check-In", readonly=True)

    employee_id = fields.Many2one(comodel_name="hr.employee",string="Employee ID", readonly=True)
    employee_name = fields.Char("Name", readonly=True)