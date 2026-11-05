# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        res.attr("has_multi_website", self.has_group("website.group_multi_website"))
