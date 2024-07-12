from odoo import api, fields, models

# The keys name the document, not the operation code: 'outgoing' is a GT, 'internal' a GA, 'incoming' a GD.
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

    @api.constrains('company_id', 'company_exclusive_series')
    def _check_l10n_pt_stock_operation_types_company(self):
        """A series assigned to an operation type stays usable by that operation type's company."""
        # sudo: the operation types of every company, not only those the editor has selected.
        self.env['stock.picking.type'].sudo().with_context(active_test=False).search([
            '|',
            ('l10n_pt_stock_at_series_id', 'in', self.ids),
            ('l10n_pt_stock_return_at_series_id', 'in', self.ids),
        ])._check_l10n_pt_stock_at_series_id()
