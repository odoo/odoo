from odoo import fields, models


class Od19BillingEvidence(models.Model):
    _inherit = "od19.billing.evidence"

    billing_request_id = fields.Many2one(
        "od19.billing.request",
        string="Billing Request",
        ondelete="cascade",
        index=True,
    )


class Od19BillingEvidenceType(models.Model):
    _inherit = "od19.billing.evidence.type"

    requires_original = fields.Boolean(
        string="Requires Original / ต้องมีต้นฉบับจริง"
    )
