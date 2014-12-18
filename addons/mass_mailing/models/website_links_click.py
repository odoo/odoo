from openerp import fields
from openerp import models


class website_links_click(models.Model):
    _inherit = "website.links.click"

    mail_stat_id = fields.Many2one('mail.mail.statistics', string='Mail Statistics')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mass Mailing')
    mass_mailing_campaign_id = fields.Many2one('mail.mass_mailing.campaign', string='Mass Mailing Campaign')
