from odoo import fields, models

from odoo.addons.mail.tools.discuss import Store


class MailActivity(models.Model):
    _inherit = "mail.activity"

    request_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Requesting Partner",
        ondelete="cascade",
    )

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [
            Store.One("request_partner_id", [])
        ]
