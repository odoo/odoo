# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons.mail.tools.discuss import Store


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['mail.thread.phone', 'res.partner']

    def _store_avatar_card_fields(self, res: Store.FieldList):
        super()._store_avatar_card_fields(res)
        if res.is_for_internal_users():
            res.extend(["phone_formatted", "phone_sanitized"])
