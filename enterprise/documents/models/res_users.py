# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class Users(models.Model):
    _name = "res.users"
    _inherit = ["res.users"]

    def _init_store_data(self, store):
        super()._init_store_data(store)
        has_group = self.env.user.has_group("documents.group_documents_user")
        store.add({"hasDocumentsUserGroup": has_group})
