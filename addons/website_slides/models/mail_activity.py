# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, tools, _
from odoo.tools import is_html_empty
from odoo.addons.mail.tools.discuss import Store


class MailActivity(models.Model):
    _inherit = "mail.activity"

    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')

    def _to_store(self, store: Store):
        super()._to_store(store)
        for activity in self.filtered(lambda a: a.request_partner_id):
            store.add(activity, {"request_partner_id": activity.request_partner_id})
