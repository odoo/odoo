from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minlength = fields.Integer("Minimum Password Length", help="Minimum number of characters passwords must contain, set to 0 to disable.")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()

        res['minlength'] = int(self.env['ir.config_parameter'].sudo().get_param('auth_password_policy.minlength', default=0))

        return res

    @api.model
    def set_values(self):
        self.env['ir.config_parameter'].sudo().set_param('auth_password_policy.minlength', self.minlength)

        super(ResConfigSettings, self).set_values()

    @api.onchange('minlength')
    def _on_change_mins(self):
        """ Password lower bounds must be naturals
        """
        self.minlength = max(0, self.minlength or 0)
