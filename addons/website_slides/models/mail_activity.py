# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.mail.tools.discuss import Store


class MailActivity(models.Model):
    _inherit = "mail.activity"

    request_partner_id = fields.Many2one("res.partner", string="Requesting Partner")

    def _to_store_defaults(self):
        return super()._to_store_defaults() + [Store.One("request_partner_id", [])]
