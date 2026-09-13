from odoo import fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    reveal_id = fields.Char(
        string="Reveal ID",
        index="btree_not_null",
    )

    def _merge_get_fields(self):
        return super()._merge_get_fields() + ["reveal_id"]
