from odoo import models, fields, _
from odoo.exceptions import UserError

AT_SERIES_MOVEMENT_DOCUMENT_TYPES = [
    ('outgoing', 'Transport Guide (GT)'),
    ('internal', 'Internal Transport Document (GA)'),
    ('incoming', 'Return Note (GD)'),
]


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    def write(self, vals):
        if 'name' in vals or 'training_series' in vals:
            for at_series in self:
                if self.env['stock.picking'].search_count([
                    ('l10n_pt_document_number', 'like', f'{at_series.name}/'),
                    ('state', "!=", 'draft'),
                ], limit=1):
                    raise UserError(_("You cannot change the name or training status of a series that has already been used."))
        return super().write(vals)


class L10nPtStockATSeriesLine(models.Model):
    _inherit = "l10n_pt.at.series.line"

    type = fields.Selection(
        selection_add=AT_SERIES_MOVEMENT_DOCUMENT_TYPES,
        ondelete={'outgoing': 'cascade', 'internal': 'cascade', 'incoming': 'cascade'}
    )

    def write(self, vals):
        if 'type' in vals or 'prefix' in vals or 'at_code' in vals:
            for at_series in self:
                if self.env['stock.picking'].search_count([
                    ('l10n_pt_document_number', '=like', f'{at_series.document_identifier}/%'),
                    ('state', "!=", 'draft'),
                ], limit=1):
                    raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
