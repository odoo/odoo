from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # === AI Extraction Fields ===
    ai_source_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='AI Source Attachment',
        ondelete='set null',
        help="The source PDF or image attachment that was processed by the AI extraction service.",
    )
    ai_ocr_text = fields.Text(
        string='AI OCR Text',
        help="Raw OCR text extracted from the source PDF/image by the AI service.",
    )
    ai_model_used = fields.Char(
        string='AI Model Used',
        help="Identifier of the AI model used for extraction.",
    )
    ai_review_required = fields.Boolean(
        string='AI Review Required',
        tracking=True,
        default=False,
        help="When checked, this document's AI extraction needs human review before posting.",
    )
    ai_extraction_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('extracted', 'Extracted'),
            ('validated', 'Validated'),
            ('failed', 'Failed'),
        ],
        string='AI Extraction Status',
        default='pending',
        index=True,
        tracking=True,
        help="Current state of AI data extraction for this document.",
    )
    ai_confidence = fields.Float(
        string='AI Overall Confidence',
        digits=(3, 2),
        tracking=True,
        help="Overall extraction confidence score between 0.00 and 1.00.",
    )
    ai_extracted_json = fields.Json(
        string='AI Extracted Raw Payload',
        help="JSON blob containing full unprocessed OCR/AI response.",
    )
    ai_extracted_on = fields.Datetime(
        string='AI Extracted On',
        readonly=True,
        help="Timestamp when data extraction completed.",
    )
    ai_validated_on = fields.Datetime(
        string='AI Validated On',
        readonly=True,
        help="Timestamp when data validation completed.",
    )
    extraction_line_ids = fields.One2many(
        comodel_name='invoice.agent.extraction.line',
        inverse_name='move_id',
        string='Per-Field Extraction Data',
    )

    # === AI Extracted Total ===
    ai_extracted_total = fields.Monetary(
        string='AI Extracted Total',
        readonly=True,
        help="Total amount extracted from the source document by the AI service.",
    )

    # === Variance ===
    ai_amount_variance = fields.Monetary(
        string='AI Amount Variance',
        compute='_compute_ai_variance',
        store=True,
        readonly=True,
        help="Difference between AI-extracted total and the system-computed total.",
    )
    ai_variance_pct = fields.Float(
        string='AI Variance %',
        compute='_compute_ai_variance',
        store=True,
        digits=(5, 4),
        readonly=True,
        help="Relative variance as a percentage of the system total.",
    )
    ai_needs_review = fields.Boolean(
        string='AI Needs Review',
        compute='_compute_ai_variance',
        store=True,
        readonly=True,
        help="Flagged when variance exceeds the journal's configured threshold.",
    )

    # === Average confidence across all invoice lines ===
    ai_line_confidence_avg = fields.Float(
        string='Line Confidence Avg',
        compute='_compute_ai_line_confidence_avg',
        store=True,
        digits=(3, 2),
        readonly=True,
        help="Average AI confidence across all invoice lines.",
    )

    # === Link to originating sale order ===
    ai_source_sale_order_id = fields.Many2one(
        comodel_name='sale.order',
        string='Source Sale Order',
        ondelete='set null',
        index=True,
        copy=False,
        help="The sale order that generated this invoice, when known from AI extraction.",
    )

    # -------------------------------------------------------------------------
    # COMPUTE: AI Variance
    # -------------------------------------------------------------------------
    @api.depends('amount_total', 'ai_extracted_total', 'currency_id')
    def _compute_ai_variance(self):
        for move in self:
            total = move.amount_total or 0.0
            ai_total = move.ai_extracted_total or 0.0
            move.ai_amount_variance = ai_total - total
            if total:
                move.ai_variance_pct = (ai_total - total) / total
            else:
                move.ai_variance_pct = 0.0
            threshold = move.journal_id.ai_min_confidence if move.journal_id.ai_agent_enabled else 0.05
            move.ai_needs_review = abs(move.ai_variance_pct) > threshold

    # -------------------------------------------------------------------------
    # COMPUTE: Average line confidence
    # -------------------------------------------------------------------------
    @api.depends('invoice_line_ids.ai_confidence')
    def _compute_ai_line_confidence_avg(self):
        for move in self:
            lines = move.invoice_line_ids.filtered(lambda l: l.ai_confidence is not None)
            if lines:
                move.ai_line_confidence_avg = sum(lines.mapped('ai_confidence')) / len(lines)
            else:
                move.ai_line_confidence_avg = 0.0

    # -------------------------------------------------------------------------
    # CONSTRAINT: Validated status requires minimum confidence
    # -------------------------------------------------------------------------
    @api.constrains('ai_confidence', 'ai_extraction_status')
    def _check_ai_confidence_validation(self):
        for move in self:
            if move.ai_extraction_status == 'validated' and move.ai_confidence is not None and move.ai_confidence < self._get_ai_min_confidence():
                raise ValidationError(_(
                    "AI extraction cannot be validated with confidence %.0f%% — "
                    "minimum %.0f%% required for journal '%s'.",
                    move.ai_confidence * 100,
                    self._get_ai_min_confidence() * 100,
                    move.journal_id.display_name,
                ))

    def _get_ai_min_confidence(self):
        self.ensure_one()
        if self.journal_id.ai_agent_enabled:
            return self.journal_id.ai_min_confidence
        return 0.70

    # -------------------------------------------------------------------------
    # VENDOR MATCHING
    # -------------------------------------------------------------------------
    def _match_vendor(self):
        self.ensure_one()
        if not self.ai_extracted_json:
            return None
        payload = self.ai_extracted_json
        partner_obj = self.env['res.partner']
        vat = payload.get('vat') or payload.get('tax_id') or payload.get('company_vat')
        if vat:
            partner = partner_obj.search(
                [('vat', '=', vat), ('parent_id', '=', False)],
                limit=1,
            )
            if partner:
                return partner
        company_name = payload.get('company_name') or payload.get('supplier_name') or payload.get('vendor_name')
        if company_name:
            partner = partner_obj.search(
                [('name', 'ilike', company_name), ('parent_id', '=', False)],
                limit=1,
            )
            if partner:
                return partner
        return None

    @api.onchange('ai_ocr_text')
    def _onchange_ai_ocr_text(self):
        if not self.ai_ocr_text:
            return {}
        if not self.ai_extracted_json:
            return {}
        partner = self._match_vendor()
        if partner:
            self.partner_id = partner
            return {}
        return {
            'warning': {
                'title': _('Vendor Not Matched'),
                'message': _(
                    'Could not automatically match a vendor from the AI-extracted data. '
                    'Please select the vendor manually from the list.'
                ),
            },
        }

    # -------------------------------------------------------------------------
    # ORM Overrides
    # -------------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if 'ai_extraction_status' in vals:
            if vals['ai_extraction_status'] == 'validated':
                self.write({'ai_validated_on': fields.Datetime.now()})
            elif vals['ai_extraction_status'] == 'extracted':
                self.write({'ai_extracted_on': fields.Datetime.now()})
        return res

    # -------------------------------------------------------------------------
    # CRON: Retry stuck extractions
    # -------------------------------------------------------------------------
    @api.model
    def _cron_retry_stuck_extractions(self):
        """Called by ir.cron every 30 minutes.
        Finds bills stuck in 'processing' for more than 1 hour
        and resets them to 'pending' so the extraction pipeline can retry.
        """
        from datetime import timedelta
        threshold = fields.Datetime.now() - timedelta(hours=1)
        stuck = self.search([
            ('ai_extraction_status', '=', 'processing'),
            ('write_date', '<', threshold),
        ])
        count = len(stuck)
        for move in stuck:
            try:
                move.write({
                    'ai_extraction_status': 'pending',
                    'ai_confidence': 0.0,
                })
            except Exception:
                _logger.exception("Cron failed to reset stuck extraction on %s", move.display_name)
        if count:
            _logger.info("_cron_retry_stuck_extractions: reset %d stuck moves from 'processing' to 'pending'", count)
        return count

    _sql_constraints = [
        (
            'check_ai_confidence_range',
            'CHECK(ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0))',
            'Overall AI Confidence score must strictly remain between 0.00 and 1.00.',
        ),
    ]
