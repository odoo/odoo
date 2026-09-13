from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    newsletter_id = fields.Many2one(
        comodel_name="mailing.list",
        string="Newsletter List",
    )
