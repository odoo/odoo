# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Users(models.Model):
    _inherit = "res.users"

    def _init_store_data(self, store):
        super()._init_store_data(store)
        domain = [("use_website_helpdesk_livechat", "=", True), ('company_id', 'in', self.env.context.get('allowed_company_ids', []))]
        helpdesk_livechat_active = self.env["helpdesk.team"].sudo().search_count(domain, limit=1)
        store.add({"helpdesk_livechat_active": bool(helpdesk_livechat_active)})
