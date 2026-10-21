from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    tutorial_preference = fields.Selection(
        [('enabled', "Enabled"), ('disabled', "Disabled")], user_writeable=True,
        help="Whether the user chose to be guided through the apps with tutorials, if they did",
    )
    tutorial_enabled = fields.Boolean(
        compute='_compute_tutorial_enabled', inverse='_inverse_tutorial_enabled',
        string="Tutorials", user_writeable=True,
        help="Guide me through the apps with tutorials, by default on a trial database",
    )
    tutorial_tips_shown = fields.Boolean(
        string="Always Show Tutorial Tips", user_writeable=True,
        help="Always show the tip of the current step of a tutorial, not only while hovering it",
    )

    @api.depends('tutorial_preference')
    def _compute_tutorial_enabled(self):
        """ The choice of the user if they made one, otherwise whether the
        database is a trial: it's only known as one after its creation (once
        the publisher warranty answered), so the default can't be stored when
        the user is created """
        in_trial = self.env['ir.config_parameter'].sudo().get_str('database.expiration_reason') == 'trial'
        for user in self:
            user.tutorial_enabled = user.tutorial_preference == 'enabled' if user.tutorial_preference else in_trial

    def _inverse_tutorial_enabled(self):
        for user in self:
            user.tutorial_preference = 'enabled' if user.tutorial_enabled else 'disabled'
