from odoo import models
from odoo.addons.mail.tools.discuss import Store


class ResUsers(models.Model):
    _inherit = "res.users"

    def _store_init_global_fields(self, res: Store.FieldList):
        super()._store_init_global_fields(res)
        res.attr("has_access_create_lead", self.has_group("sales_team.group_sale_salesman"))
