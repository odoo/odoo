from odoo import _, fields, models
from odoo.exceptions import UserError

AT_SERIES_MOVEMENT_DOCUMENT_TYPES = [
    ('outgoing', 'Transport Guide (GT)'),
    ('internal', 'Internal Transport Document (GA)'),
    ('incoming', 'Return Note (GD)'),
]


class L10nPtATSeries(models.Model):
    _inherit = "l10n_pt.at.series"

    def _has_stock_pickings(self):
        self.ensure_one()
        return self.env['stock.picking'].search_count([
            ('l10n_pt_at_series_id', '=', self.id),
            ('state', 'in', ('done', 'cancel')),
        ], limit=1)

    def write(self, vals):
        if 'name' in vals or 'training_series' in vals:
            for at_series in self:
                if at_series._has_stock_pickings():
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
            for at_series_line in self:
                if at_series_line.at_series_id._has_stock_pickings():
                    raise UserError(_("You cannot change the type, prefix or AT code of a series that has already been used."))
        return super().write(vals)
