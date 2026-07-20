import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
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

    def write(self, vals):
        _logger.info("account.move.write on %s → changed keys: %s", self.ids, list(vals.keys()))
        return super().write(vals)
