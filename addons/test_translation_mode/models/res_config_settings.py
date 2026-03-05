from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    language = fields.Selection(related='user_id.lang', readonly=False)
    translation_url = fields.Char(
        string="Weblate URL",
        config_parameter='test_translation_mode.translation_url',
        help="Set the weblate URL where the translations are hosted"
    )

    def save_and_reload(self):
        self.set_values()
        return {'type': 'ir.actions.client', 'tag': 'reload'}
