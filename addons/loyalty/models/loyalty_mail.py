# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


# Allow promo programs to send mails upon certain triggers
# Like : 'At creation' and 'When reaching X points'


class LoyaltyMail(models.Model):
    _name = 'loyalty.mail'
    _description = "Loyalty Communication"

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(comodel_name='loyalty.program', ondelete='cascade', required=True, index=True)
    trigger = fields.Selection(
        string="When",
        selection=[
            ('create', "At Creation"),
            ('points_reach', "When Reaching")
        ],
        required=True,
    )
    points = fields.Float()
    mail_template_id = fields.Many2one(
        string="Email Template",
        comodel_name='mail.template',
        ondelete='cascade',
        domain=[('model', '=', 'loyalty.card')],
        required=True,
    )
