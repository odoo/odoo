from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    ai_invoice_count = fields.Integer(
        string="AI Invoices Processed",
        compute="_compute_ai_invoice_stats",
        readonly=True,
        help="Number of invoices processed via AI for this partner.",
    )
    ai_avg_confidence = fields.Float(
        string="AI Avg Confidence",
        compute="_compute_ai_invoice_stats",
        digits=(3, 2),
        readonly=True,
        help="Average AI extraction confidence across all invoices for this partner.",
    )

    def init(self):
        """Create partial index to accelerate vendor VAT matching.

        Optimizes queries searching for top-level vendors by matching VAT:
        search([('vat', '=', ...), ('parent_id', '=', False)])
        """
        # Fix 1 & 2: Use self.env.cr directly and check for NULL instead of 0
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS res_partner_vat_parent_idx
            ON res_partner (vat)
            WHERE parent_id IS NULL AND vat IS NOT NULL
            """)

    @api.depends("invoice_ids.ai_confidence", "invoice_ids.move_type")
    def _compute_ai_invoice_stats(self):
        # Fix 4: Performance optimization using read_group to prevent N+1 queries
        partners = self.filtered("id")
        if not partners:
            return

        for partner in self:
            partner.ai_invoice_count = 0
            partner.ai_avg_confidence = 0.0

        # Group data efficiently at database level
        data = self.env["account.move"].read_group(
            domain=[
                ("partner_id", "in", partners.ids),
                ("move_type", "in", ("in_invoice", "in_refund")),
                ("ai_confidence", "!=", False),
            ],
            fields=["partner_id", "ai_confidence:avg", "id:count"],
            groupby=["partner_id"],
        )

        for row in data:
            partner = self.browse(row["partner_id"][0])
            partner.ai_invoice_count = row["partner_id_count"]
            partner.ai_avg_confidence = row["ai_confidence"] or 0.0
