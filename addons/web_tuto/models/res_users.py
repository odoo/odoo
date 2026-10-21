from odoo import api, fields, models, modules


class ResUsers(models.Model):
    _inherit = 'res.users'

    def _default_tutorial_enabled(self):
        demo_modules_count = self.env['ir.module.module'].sudo().search_count([('demo', '=', True)], limit=1)
        return demo_modules_count == 0 and not modules.module.current_test

    tutorial_enabled = fields.Boolean(default=_default_tutorial_enabled, string="Tutorials")

    @api.model
    def switch_tutorial_enabled(self, val):
        self.env.user.sudo().tutorial_enabled = val
        return self.env.user.tutorial_enabled
