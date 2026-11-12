from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    od19_website_tagline = fields.Char(
        string="Website Tagline",
        translate=True,
        default="Total Integrated Automation Solutions",
        help="Short tagline shown on the website homepage hero section.",
    )
    od19_website_primary_color = fields.Char(
        string="Website Primary Color",
        default="#9E2424",
        help="Primary brand color used across the website (hex).",
    )
    od19_website_secondary_color = fields.Char(
        string="Website Secondary Color",
        default="#f39200",
        help="Secondary / accent brand color used across the website (hex).",
    )
    od19_website_hero_title = fields.Char(
        string="Hero Title",
        translate=True,
        default="Automation Solutions for a Smarter Future",
    )
    od19_website_hero_subtitle = fields.Char(
        string="Hero Subtitle",
        translate=True,
        default="Industrial · Building · Terminal Automation",
    )
    od19_website_facebook_url = fields.Char(string="Facebook URL")
    od19_website_linkedin_url = fields.Char(string="LinkedIn URL")
    od19_website_youtube_url = fields.Char(string="YouTube URL")
    od19_website_cert_body = fields.Char(
        string="Certification Body",
        help="Accredited certification body that issued the ISO 9001 certificate "
             "(e.g. shown on /quality-certifications).",
    )
    od19_website_cert_no = fields.Char(
        string="Certificate Number",
        help="ISO 9001 certificate number shown on the quality page.",
    )
    od19_website_cert_valid_until = fields.Date(
        string="Certificate Valid Until",
        help="Expiry date of the ISO 9001 certificate.",
    )
    od19_website_ga_key = fields.Char(
        string="Google Analytics ID",
        help="Google Analytics 4 measurement ID (G-XXXXXXXXXX). When set, it is "
             "propagated to the website and the analytics script is loaded with "
             "Odoo's cookie-consent gating (analytics denied until the visitor "
             "accepts optional cookies).",
    )
