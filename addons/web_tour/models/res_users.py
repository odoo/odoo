from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = "res.users"

    tour_enabled = fields.Boolean()

    @api.model
    def switch_tour_enabled(self, val):
        self.env.user.sudo().tour_enabled = val
        return self.env.user.tour_enabled
