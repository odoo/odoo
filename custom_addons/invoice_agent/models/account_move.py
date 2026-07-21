from odoo import fields, models


#  this file extends the account.move model to add fields and functionality for AI-based data extraction for invoices and journal entries.
class AccountMove(models.Model):
    _inherit = 'account.move'
    # Add AI Extraction Fields
    # These fields are used to track the status and results of AI-based data extraction for invoices and journal entries.

    # the current status of the AI extraction process for this document
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
    # the overall confidence score of the AI extraction process for this document
    ai_confidence = fields.Float(
        string='AI Overall Confidence',
        digits=(3, 2),
        tracking=True,
        help="Overall extraction confidence score between 0.00 and 1.00.",
    )
    # the raw JSON payload returned by the AI extraction service for this document
    ai_extracted_json = fields.Json(
        string='AI Extracted Raw Payload',
        help="JSON blob containing full unprocessed OCR/AI response.",
    )
    #  the timestamp when the AI extraction process completed for this document
    ai_extracted_on = fields.Datetime(
        string='AI Extracted On',
        readonly=True,
        help="Timestamp when data extraction completed.",
    )
    # the timestamp when the AI extraction process was validated for this document
    ai_validated_on = fields.Datetime(
        string='AI Validated On',
        readonly=True,
        help="Timestamp when data validation completed.",
    )
    # the attachment record corresponding to the processed scan
    ai_scan_pdf_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='AI Scan PDF',
        ondelete='set null',
        help="Attachment record corresponding to the processed scan.",
    )
    # the attachment record corresponding to the processed OCR text
    ai_scan_text_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='AI Scan Text',
        ondelete='set null',
        help="Attachment record corresponding to the processed OCR text.",
    )
    # the attachment record corresponding to the processed AI JSON payload
    ai_scan_json_id = fields.Many2one(
        comodel_name='ir.attachment',
        string='AI Scan JSON',
        ondelete='set null',
        help="Attachment record corresponding to the processed AI JSON payload.",
    )
    # the one-to-many relationship to the per-field extraction lines for this document
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
