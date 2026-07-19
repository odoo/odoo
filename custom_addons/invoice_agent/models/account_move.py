from odoo import fields, models


class AccountMove(models.Model):
    """Inherits account.move to add AI pipeline tracking fields."""

    _inherit = "account.move"

    ai_extraction_status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("success", "Success"),
            ("failed", "Failed"),
        ],
        string="AI Extraction Status",
        default="pending",
        help="Tracks the processing status of the AI Invoice Agent pipeline.",
    )
