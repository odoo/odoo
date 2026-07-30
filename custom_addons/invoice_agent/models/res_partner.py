from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ai_invoice_count = fields.Integer(
        string='AI Invoices Processed',
        compute='_compute_ai_invoice_stats',
        readonly=True,
        help="Number of invoices processed via AI for this partner.",
    )
    ai_avg_confidence = fields.Float(
        string='AI Avg Confidence',
        compute='_compute_ai_invoice_stats',
        digits=(3, 2),
        readonly=True,
        help="Average AI extraction confidence across all invoices for this partner.",
    )

    @api.depends('invoice_ids.ai_confidence', 'invoice_ids.move_type')
    def _compute_ai_invoice_stats(self):
        for partner in self:
            ai_invoices = partner.invoice_ids.filtered(
                lambda m: m.move_type in ('in_invoice', 'in_refund')
                and m.ai_confidence is not None,
            )
            partner.ai_invoice_count = len(ai_invoices)
            if ai_invoices:
                partner.ai_avg_confidence = sum(ai_invoices.mapped('ai_confidence')) / len(ai_invoices)
            else:
                partner.ai_avg_confidence = 0.0
