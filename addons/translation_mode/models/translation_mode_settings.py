from odoo import models, fields


class TranslationModeSettings(models.TransientModel):
    _name = 'translation_mode.settings'
    _description = "Translation Mode Settings"

    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    language = fields.Selection(related='user_id.lang', readonly=False)
    translation_url = fields.Char(string="Weblate URL",
        compute='_compute_translation_url',
        inverse='_inverse_translation_url',
        help="Set the weblate URL where the translations are hosted")

    def save_and_reload(self):
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def _compute_translation_url(self):
        for record in self:
            record.translation_url = self.env['ir.config_parameter'].sudo().get_str('translation_mode.translate_url') or ''

    def _inverse_translation_url(self):
        for record in self:
            self.env['ir.config_parameter'].sudo().set_str('translation_mode.translate_url', record.translation_url or '')
