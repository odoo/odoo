# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class ResUsersSettings(models.Model):
    _inherit = 'res.users.settings'

    livechat_username = fields.Char("Livechat Username", help="This username will be used as your name in the livechat channels.")
    livechat_lang_ids = fields.Many2many(comodel_name='res.lang', string='Livechat languages',
                            help="These languages, in addition to your main language, will be used to assign you to Live Chat sessions.")
    livechat_expertise_ids = fields.Many2many(
        "im_livechat.expertise",
        string="Live Chat Expertise",
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
    )
    livechat_push = fields.Boolean(default=True)

    def _store_settings_fields(self, res: Store.FieldList):
        super()._store_settings_fields(res)
        res.extend([
            "livechat_username", "livechat_lang_ids", "livechat_expertise_ids", "livechat_push",
        ])
