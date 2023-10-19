from odoo import models, fields,api

class Profile(models.Model):
    _name = "profile"
    _description = "Description of the Profile model"
    name = fields.Char()
    days_of_delivery = fields.Char()
    no_hours = fields.Integer(string='No Hours', compute='compute_total_hours', store=True)
    contract_ids = fields.One2many('contract',"period_id", string='Contracts')
    details_ids = fields.One2many('profile_details',"profile_id", string='Details')

    @api.depends('details_ids')
    def compute_total_hours(self):
        for profile in self:
            total_hours = sum(detail.end-detail.start for detail in profile.details_ids)
            profile.no_hours = total_hours
