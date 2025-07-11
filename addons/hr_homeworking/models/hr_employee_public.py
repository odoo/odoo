from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    monday_location_id = fields.Many2one('hr.work.location', string='Monday')
    tuesday_location_id = fields.Many2one('hr.work.location', string='Tuesday')
    wednesday_location_id = fields.Many2one('hr.work.location', string='Wednesday')
    thursday_location_id = fields.Many2one('hr.work.location', string='Thursday')
    friday_location_id = fields.Many2one('hr.work.location', string='Friday')
    saturday_location_id = fields.Many2one('hr.work.location', string='Saturday')
    sunday_location_id = fields.Many2one('hr.work.location', string='Sunday')
    today_location_name = fields.Char()

    hr_icon_display = fields.Selection(selection_add=[('presence_home', 'At Home'),
                                                    ('presence_office', 'At Office'),
                                                    ('presence_other', 'At Other')])
