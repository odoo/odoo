from odoo import fields, models

# Keys kept from when the type followed the operation code; they now name the document only.
AT_SERIES_MOVEMENT_DOCUMENT_TYPES = [
    ('outgoing', 'Transport Guide (GT)'),
    ('internal', 'Own Fixed Assets Movement Guide (GA)'),
    ('incoming', 'Return Note (GD)'),
]


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    document_type = fields.Selection(
        selection_add=AT_SERIES_MOVEMENT_DOCUMENT_TYPES,
        ondelete={'outgoing': 'cascade', 'internal': 'cascade', 'incoming': 'cascade'},
    )
