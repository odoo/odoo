from odoo import fields, models


class SocialMediaConfig(models.Model):
    _name = "social_media.config"
    _description = "A company's social media configuration"
    _inherit = ["mixin.company.config"]

    social_twitter = fields.Char(string="X Account")
    social_facebook = fields.Char(string="Facebook Account")
    social_github = fields.Char(string="GitHub Account")
    social_linkedin = fields.Char(string="LinkedIn Account")
    social_youtube = fields.Char(string="Youtube Account")
    social_instagram = fields.Char(string="Instagram Account")
    social_tiktok = fields.Char(string="TikTok Account")
    social_discord = fields.Char(string="Discord Account")
