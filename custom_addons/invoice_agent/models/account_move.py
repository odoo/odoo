from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    # === AI Extraction Fields ===

    # The source attachment (PDF scan) that was processed by the AI
    ai_source_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='AI Source Attachment',
        ondelete='set null',
        help="The source PDF or image attachment that was processed by the AI extraction service.",
    )

    # The raw OCR text extracted from the source document
    ai_ocr_text = fields.Text(
        string='AI OCR Text',
        help="Raw OCR text extracted from the source PDF/image by the AI service.",
    )

    # The AI model identifier used for extraction (e.g. 'gpt-4o', 'llama-3.1-70b')
    ai_model_used = fields.Char(
        string='AI Model Used',
        help="Identifier of the AI model used for extraction (e.g. 'gpt-4o', 'llama-3.1-70b').",
    )

    # Flag indicating the extraction needs human review before use
    ai_review_required = fields.Boolean(
        string='AI Review Required',
        tracking=True,
        default=False,
        help="When checked, this document's AI extraction needs human review before posting.",
    )

    # The current status of the AI extraction process for this document
    ai_extraction_status = fields.Selection(
        selection=[
            ('pending', 'Pending'),
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

    # The overall confidence score of the AI extraction process for this document
    ai_confidence = fields.Float(
        string='AI Overall Confidence',
        digits=(3, 2),
        tracking=True,
        help="Overall extraction confidence score between 0.00 and 1.00.",
    )

    # The raw JSON payload returned by the AI extraction service for this document
    ai_extracted_json = fields.Json(
        string='AI Extracted Raw Payload',
        help="JSON blob containing full unprocessed OCR/AI response.",
    )

    # The timestamp when the AI extraction process completed for this document
    ai_extracted_on = fields.Datetime(
        string='AI Extracted On',
        readonly=True,
        help="Timestamp when data extraction completed.",
    )

    # The timestamp when the AI extraction process was validated for this document
    ai_validated_on = fields.Datetime(
        string='AI Validated On',
        readonly=True,
        help="Timestamp when data validation completed.",
    )

    # The one-to-many relationship to the per-field extraction lines for this document
    extraction_line_ids = fields.One2many(
        comodel_name='invoice.agent.extraction.line',
        inverse_name='move_id',
        string='Per-Field Extraction Data',
    )

    # SQL constraint to ensure AI confidence is within valid range
    _sql_constraints = [
        (
            'check_ai_confidence_range',
            'CHECK(ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0))',
            'Overall AI Confidence score must strictly remain between 0.00 and 1.00.',
        ),
    ]
