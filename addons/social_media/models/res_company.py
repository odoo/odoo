from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    social_twitter = fields.Char(string="X Account")
    social_facebook = fields.Char(string="Facebook Account")
    social_github = fields.Char(string="GitHub Account")
    social_linkedin = fields.Char(string="LinkedIn Account")
    social_youtube = fields.Char(string="Youtube Account")
    social_instagram = fields.Char(string="Instagram Account")
    social_tiktok = fields.Char(string="TikTok Account")
    social_discord = fields.Char(string="Discord Account")
