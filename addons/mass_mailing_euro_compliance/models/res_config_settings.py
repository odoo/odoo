from odoo import Command, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    restrict_mail_tracking = fields.Boolean(config_parameter="mass_mailing.restrict_mail_tracking")
    default_disable_open_tracking = fields.Boolean(default_model="mailing.mailing")
    default_disable_click_tracking = fields.Boolean(default_model="mailing.mailing")

    default_blacklisted_country_ids = fields.Many2many('res.country', default_model="mailing.mailing")

    @api.model
    def get_values(self):
        res = super().get_values()
        country_ids = self.env['ir.default'].sudo()._get('mailing.mailing', 'blacklisted_country_ids') or []
        res['default_blacklisted_country_ids'] = [
            Command.set(self.env['res.country'].browse(country_ids).exists().ids),
        ]
        return res

    def set_values(self):
        if not self.restrict_mail_tracking:
            self.update({
                'default_disable_open_tracking': False,
                'default_disable_click_tracking': False,
                'default_blacklisted_country_ids': [Command.clear()],
            })
        super().set_values()
