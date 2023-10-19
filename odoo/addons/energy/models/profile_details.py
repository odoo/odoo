from odoo import models, fields

class ProfileDetails(models.Model):
    _name = "profile_details"
    _description = "Description of the Profile details model"
    profile_id = fields.Many2one('profile', string='Profile')
    start = fields.Integer(string='Start')
    end = fields.Integer(string='end')
    days = fields.Char()
