from odoo import models, fields


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('grant_approval', 'Grant Approval')], ondelete={'grant_approval': 'set default'})
