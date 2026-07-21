# this model represents a single field extraction result for an invoice or journal entry, linked to the parent account.move record. It stores the field name, extracted value, and confidence score for that specific field.
from odoo import fields, models


class InvoiceAgentExtractionLine(models.Model):
    _name = 'invoice.agent.extraction.line'
    _description = 'Invoice Agent Per-Field Extraction Line'
    # the many-to-one relationship to the parent account.move record
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Journal Entry / Invoice',
        required=True,
        ondelete='cascade',
        index=True,
    )
    # the name of the field that was extracted (e.g., "Invoice Date", "Total Amount")
    field_name = fields.Char(
        string='Field Name',
        required=True,
    )
    # the raw value extracted for this field
    extracted_value = fields.Text(
        string='Extracted Raw Value',
    )
    # the confidence score for this specific field extraction, between 0.00 and 1.00
    field_confidence = fields.Float(
        string='Field Confidence',
        digits=(3, 2),
    )
    # SQL constraint to ensure field confidence is within valid range
    _sql_constraints = [
        (
            'check_field_confidence_range',
            'CHECK(field_confidence IS NULL OR (field_confidence >= 0.0 AND field_confidence <= 1.0))',
            'Line Field Confidence score must strictly remain between 0.00 and 1.00.',
        ),
    ]
