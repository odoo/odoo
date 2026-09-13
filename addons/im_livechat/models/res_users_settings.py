from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    livechat_username = fields.Char(
        help="This username will be used as your name in the livechat channels."
    )
    livechat_lang_ids = fields.Many2many(
        comodel_name="res.lang",
        string="Livechat languages",
        help="These languages, in addition to your main language, will be used to assign you to Live Chat sessions.",
    )
    livechat_expertise_ids = fields.Many2many(
        comodel_name="im_livechat.expertise",
        string="Live Chat Expertise",
        help="When forwarding live chat conversations, the chatbot will prioritize users with matching expertise.",
    )
