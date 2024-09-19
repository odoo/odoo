from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = "res.users"

    tour_enabled = fields.Boolean(compute='_compute_tour_enabled', store=True, readonly=False)

    @api.depends("create_date")
    def _compute_tour_enabled(self):
        demo_modules_count = self.env['ir.module.module'].sudo().search_count([('demo', '=', True)])
        for user in self:
            user.tour_enabled = user._is_admin() and demo_modules_count == 0

    @api.model
    def switch_tour_enabled(self, val):
        self.env.user.sudo().tour_enabled = val
        return self.env.user.tour_enabled
