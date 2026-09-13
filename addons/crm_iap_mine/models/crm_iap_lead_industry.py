from odoo import fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class CrmIapLeadIndustry(models.Model):
    _name = "crm.iap.lead.industry"
    _description = "CRM IAP Lead Industry"
    _order = "sequence,id"

    name = fields.Char(
        string="Industry",
        translate=True,
        required=True,
    )
    reveal_ids = fields.Char(required=True)
    color = fields.Integer(string="Color Index")
    sequence = fields.Integer()

    _name_src_uniq = name_uniq_index(
        message="Industry name already exists!",
    )
