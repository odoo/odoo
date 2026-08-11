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
        """Create the partial index that accelerates vendor VAT matching.

        The extraction pipeline matches suppliers with
        ``search([("vat", "=", ...), ("parent_id", "=", False)])`` — a query
        PostgreSQL can serve with an index *only* if the index covers both
        the ``vat`` column and the ``parent_id = False`` predicate. A plain
        index on ``vat`` alone leaves PostgreSQL scanning the parent rows
        out. This partial index covers exactly the rows the pipeline looks
        up and is created idempotently (``CREATE INDEX IF NOT EXISTS``) via
        ``init()`` — the ORM hook that runs at module install/upgrade on the
        raw cursor.

        Verify with production-sized data:
            EXPLAIN ANALYZE
            SELECT id FROM res_partner
            WHERE vat = 'X' AND parent_id = FALSE;
        — it must use an Index Scan on ``res_partner_vat_parent_idx``, never a
        Seq Scan.
        """
        self._cr.execute(
            """
            CREATE INDEX IF NOT EXISTS res_partner_vat_parent_idx
            ON res_partner (vat)
            WHERE parent_id = 0 AND vat IS NOT NULL
            """,
        )

    @api.depends("invoice_ids.ai_confidence", "invoice_ids.move_type")
    def _compute_ai_invoice_stats(self):
        for partner in self:
            ai_invoices = partner.invoice_ids.filtered(
                lambda m: (
                    m.move_type in ("in_invoice", "in_refund")
                    and m.ai_confidence is not None
                ),
            )
            partner.ai_invoice_count = len(ai_invoices)
            if ai_invoices:
                partner.ai_avg_confidence = sum(
                    ai_invoices.mapped("ai_confidence"),
                ) / len(ai_invoices)
            else:
                partner.ai_avg_confidence = 0.0
