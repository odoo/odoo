from odoo import fields, models

# Allow promo programs to send mails 'At Creation' or 'When Reaching' X points


class LoyaltyMail(models.Model):
    _name = "loyalty.mail"
    _description = "Loyalty Communication"

    active = fields.Boolean(default=True)
    program_id = fields.Many2one(
        comodel_name="loyalty.program",
        index=True,
        required=True,
        ondelete="cascade",
    )
    trigger = fields.Selection(
        selection=[("create", "At Creation"), ("points_reach", "When Reaching")],
        string="When",
        required=True,
    )
    points = fields.Float()
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Email Template",
        required=True,
        domain=[("model", "=", "loyalty.card")],
        ondelete="cascade",
    )
