from odoo import fields, models


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    approval_type = fields.Selection(
        selection_add=[
            ("maintenance_preventive", "Maintenance - Preventive"),
            ("maintenance_corrective", "Maintenance - Corrective"),
        ],
        ondelete={
            "maintenance_preventive": "cascade",
            "maintenance_corrective": "cascade",
        },
    )
