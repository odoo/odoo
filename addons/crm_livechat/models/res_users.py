from odoo import models
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    def _init_store_data(self, store: Store):
        super()._init_store_data(store)
        store.add_global_values(has_access_create_lead=self.env.user.has_group("sales_team.group_sale_salesman"))
