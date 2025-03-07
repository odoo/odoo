from odoo import fields, models

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    plan_id = fields.Many2one('mail.activity.plan', string='Plan')
