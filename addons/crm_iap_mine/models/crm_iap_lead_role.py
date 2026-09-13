from odoo import api, fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class CrmIapLeadRole(models.Model):
    _name = "crm.iap.lead.role"
    _description = "People Role"

    name = fields.Char(
        string="Role Name",
        translate=True,
        required=True,
    )
    reveal_id = fields.Char(required=True)
    color = fields.Integer(string="Color Index")

    _name_src_uniq = name_uniq_index(
        message="Role name already exists!",
    )

    def _compute_display_name(self):
        for role in self:
            role.display_name = (role.name or "").replace("_", " ").title()
