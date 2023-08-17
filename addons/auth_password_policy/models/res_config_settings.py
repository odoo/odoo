from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    minlength = fields.Integer(
        "Minimum Password Length", config_parameter="auth_password_policy.minlength", default=0,
        help="Minimum number of characters passwords must contain, set to 0 to disable.")

    password_leak_check_enabled = fields.Boolean(
        "Password Leak Check Enabled",
        config_parameter='auth_password_policy.leak_check_enabled',
        required=True,
    )
    password_leak_check_frequency_count = fields.Integer(
        'Password Leak Check Frequency Count',
        config_parameter='auth_password_policy.leak_check_frequency_count',
        required=True,
    )
    password_leak_check_frequency_unit = fields.Selection(
        [('hours', 'Hours'),
         ('days', 'Days'),
         ('months', 'Months')],
        string='Password Leak Check Frequency Unit',
        config_parameter='auth_password_policy.leak_check_frequency_unit',
        required=True,
    )

    @api.onchange('minlength')
    def _on_change_mins(self):
        """ Password lower bounds must be naturals
        """
        self.minlength = max(0, self.minlength or 0)

    @api.onchange('password_leak_check_frequency_count')
    def _on_change_check_frequency_count(self):
        self.password_leak_check_frequency_count = max(1, self.password_leak_check_frequency_count)
