from odoo import fields, models


class CrmTag(models.Model):
    _name = "crm.tag"
    _inherit = ["mixin.tag.nested"]
    _description = "CRM Tag"

    parent_id = fields.Many2one(
        comodel_name="crm.tag",
        string="Parent Tag",
        index=True,
        ondelete="cascade",
    )
    child_ids = fields.One2many(
        comodel_name="crm.tag",
        inverse_name="parent_id",
        string="Child Tags",
    )
