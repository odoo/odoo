from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    qbo_mapping_ids = fields.One2many(
        "qbo.company.mapping",
        "company_id",
        string="QBO realm mappings",
    )
    qbo_connected = fields.Boolean(
        compute="_compute_qbo_connected",
        string="QBO connected",
        store=False,
    )

    def _compute_qbo_connected(self):
        for rec in self:
            rec.qbo_connected = any(
                m.realm_id.state == "connected"
                for m in rec.qbo_mapping_ids
                if m.sync_enabled
            )
